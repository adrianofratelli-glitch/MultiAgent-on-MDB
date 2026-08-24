# CLAUDE.md

Este arquivo orienta o Claude Code (claude.ai/code) ao trabalhar com o código deste repositório.

## Projeto

PoV enterprise de um sistema multi-agente de atendimento ao cliente em que o MongoDB Atlas é ao mesmo tempo o plano de dados e o plano de coordenação. Regras de roteamento, estado dos agentes, handoffs, memória, cache, decisões de guardrail e histórico de eval vivem todos como documentos no MongoDB e são consultáveis como qualquer outro dado operacional. Veja `docs/architecture.md` e `docs/adr/ADR-001-arquitetura-multi-agente.md` para o racional completo (por que MongoDB em vez de uma fila/motor de workflow).

8 agentes reais no `agent_registry`: `orchestrator`, `order_agent`, `product_agent`, `support_agent`, `billing_agent`, `warranty_agent`, `loyalty_agent`, `logistics_agent`. Se o registry diz N agentes, N deles respondem — uma iteração anterior o encheu com ~120 documentos inertes "adormecidos" para alegar "100+ agentes"; isso foi revertido de propósito. Não reintroduza documentos inúteis só para inflar uma contagem.

A documentação e os textos da UI estão em português; código e comentários seguem em inglês.

## Comandos

Setup:
```bash
cp .env.example .env
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/seed.py   # também invalida semantic_cache/short_term_memory: respostas em cache derivam do mundo anterior
```

Rodar o backend (porta 8031, estrito — sai se estiver ocupada, sem fallback automático):
```bash
cd backend && python run.py
```

Rodar o backend sem Atlas (store em memória, mesmos dados de seed/contratos, sem Search/Vector Search/Change Streams reais):
```bash
cd backend && DEMO_MODE=1 AUTH_REQUIRED=1 python run.py
```

Rodar o frontend (porta 5191, estrito):
```bash
cd frontend && npm install && npm run dev
```

Testes do backend:
```bash
cd backend && pytest -q                                  # testes unitários, suíte completa
cd backend && pytest tests/test_router.py -q              # um arquivo
cd backend && pytest tests/test_router.py::test_name -q   # um teste
python backend/tests/smoke.py http://127.0.0.1:8031        # smoke test caixa-preta contra um servidor rodando; sai com código não-zero em falha
python backend/eval.py http://127.0.0.1:8031               # eval de golden dataset (seed_data.py:EVAL_CASES), grava histórico de pass/fail em eval_runs
cd backend && python calibrate_thresholds.py               # mede a faixa de score da denylist contra probes rotuladas (--apply grava vector_threshold em guardrail_policies)
```

Antes de uma demo ao vivo, pré-aqueça o cache semântico para que o primeiro clique do cliente não seja uma cadeia multi-hop fria de LLM:
```bash
python backend/warmup.py http://127.0.0.1:8031
```
Isso chama de verdade cada cenário marcado para warmup, uma vez por identidade, contra a Anthropic, e então verifica quais respostas foram admitidas pela política `stable_v1`. Só turnos estáveis de catálogo/base de conhecimento, sem memória do cliente, handoffs ou escritas, entram no `semantic_cache`; respostas operacionais de pedido/fatura/garantia/entrega/fidelidade permanecem no escopo da sessão mesmo quando marcadas como candidatas a warmup. O script reporta os dois desfechos explicitamente.

Lint do backend (ruff configurado no `pyproject.toml`, sem script wrapper):
```bash
cd backend && ruff check .
```

Build do frontend: `cd frontend && npm run build` (não há script de lint/test no frontend).
A CI roda os testes do backend e o build do frontend a cada push/PR.

## Arquitetura

**Fluxo:** frontend (React/Vite, `frontend/src/api.js`) → REST → backend (FastAPI, `backend/app/main.py`), autenticação JWT bearer via `/api/auth/token`, ações administrativas (ligar/desligar um agente, ver histórico de eval) protegidas pelo cabeçalho `X-Admin-Key`.

**Orquestração** (`backend/app/orchestration.py`, `router.py`, `agents.py`): cada turno passa por um guardrail de entrada e então é roteado por uma regra determinística barata (`multiagent_brain.routing_rules`) ou, apenas se nenhuma regra casar, o LLM orquestrador classifica a intenção. **O LLM nunca sobrepõe uma decisão determinística já confiante** — quando podia, a variância de amostragem tornava o roteamento não reprodutível entre mensagens quase idênticas. O desempate do `cheap_route` é pelo `priority` semeado; intenções mais específicas (`garantia`/`fidelidade`/`logistica`) são semeadas acima das genéricas (`status_pedido`/`fatura`), para que uma mensagem composta caia no primeiro agente certo. Um turno pode encadear até `MAX_HOPS = 4` agentes (por exemplo `support_agent` diagnostica → `product_agent` recomenda → `order_agent` processa a troca, sua única escrita restrita → `billing_agent`/`logistics_agent` confirma o desdobramento); cada handoff é persistido em `agent_handoffs`/`agent_traces` e alimenta o Timeline/Inspector da UI. Já uma pergunta composta genuinamente independente (status do pedido + fatura) faz fan-out de `order_agent` + `billing_agent` em paralelo via `asyncio.gather` (`router.py:detect_fanout`, `orchestration.py:_run_fanout`) em vez de encadear — restrito a esse par de propósito, já que `support_agent`/`product_agent` têm uma dependência real de diagnosticar-e-então-recomendar. As instruções de grounding de cada agente (`agents.py:GROUNDING_RULES`) mandam ignorar silenciosamente as partes de uma mensagem composta fora do próprio domínio, em vez de comentá-las — sem isso, agentes no meio da cadeia alucinam políticas de domínios que não são deles.

**Configuração de agente é dado, não código**: `multiagent_brain.agent_registry` guarda o modelo, a persona, as ferramentas e o orçamento de cada agente — editáveis em tempo de execução sem redeploy (modelo `AgentUpdate` em `backend/app/models.py`).

**Respostas ancoradas por LLM** (`agents.py:llm_synthesize`): a recuperação continua 100% determinística e segura quanto a propriedade do dado (query Mongo construída em Python, nunca pelo modelo), mas a frase final é gerada pela Anthropic sobre o(s) documento(s) *já recuperado(s)* — o que cobre formulações arbitrárias, e não apenas intenções templadas. Cai para um template de f-string quando não há chave de API ou a chamada falha, de modo que `DEMO_MODE`/CI seguem determinísticos.

**Ações de escrita** (além da atualização de status do `order_agent`, restrita a uma allowlist de valores aprovados): o `support_agent` abre um documento real em `support_tickets` em caso de escalonamento explícito ("atendente"/"chamado"/"escalar" — e não por "sem evidência na KB", já que o fallback de ranking local do `DEMO_MODE` sempre devolve *algum* artigo, relevante ou não); o `loyalty_agent` processa um resgate real de pontos (`$inc` em `loyalty_accounts.points`, restrito a uma tabela fixa de custos `REWARD_CATALOG`, mais um documento de auditoria em `redemptions`) ou faz handoff para o `product_agent` no caso de "resgatar pontos por um produto"; o `logistics_agent` pode marcar `shipments.reschedule_requested: true` (um único campo restrito). O handoff pós-escrita do `order_agent` para `billing_agent`/`logistics_agent` roda independentemente de o status ter *de fato mudado* neste turno — depender de uma mudança de estado no turno fazia com que repetir "quero trocar" depois de um turno/caso de eval anterior já ter virado o pedido derrubasse o handoff em silêncio.

**Modelo de segurança** (`backend/app/security.py`, `policies.py`, `guardrails.py`): a `customer_key` vem apenas do JWT, nunca do payload da requisição — toda query é filtrada por ela, com os filtros reconstruídos no servidor. As conversas são limitadas (20 mensagens / TTL de 24h, retomáveis via `GET /api/conversations/latest`, que também reproduz a timeline do último turno para que uma sessão retomada não pareça vazia); eventos de auditoria expiram em 30 dias. O `budget.py` aplica orçamentos de token por turno (`BudgetExceeded`); o `rate_limit.py` é um limitador de janela deslizante.
Fora do ambiente `development`, a inicialização falha fechada a menos que a autenticação seja exigida, os segredos atinjam o
comprimento mínimo, o CORS seja explícito e a emissão de token de demo esteja desabilitada. O `/metrics`
exige `X-Admin-Key`; o health nunca retorna exceções cruas do driver.

**Guardrail auto-reforçado** (`guardrails.py:check_input`): três camadas, da mais barata para a mais cara. (1) Denylist estática por substring — apenas frase exata. (2) **Denylist semântica via Atlas Vector Search** (`denylist_autoembed_v1` em `guardrail_denylist.phrase`, autoEmbed voyage-4, pré-filtrado por `area` + `layer`): é isso que bloqueia uma *paráfrase*, de forma determinística e sem uma chamada ao LLM, e continua funcionando quando o `skip_semantic` desativa o classificador ou quando a mensagem já casou com uma regra de roteamento. (3) O classificador LLM abaixo, para formulações que nenhuma das listas ainda conhece.

Dois invariantes aqui, ambos aprendidos por medição (`backend/calibrate_thresholds.py`): o `vector_threshold` em `guardrail_policies` é **medido contra probes de paráfrase, nunca chutado** — calibrar com quase-cópias da frase semeada o fixa na faixa de "texto idêntico" e reverte o guardrail a apenas match exato; e as entradas lexicais são excluídas do índice vetorial pelo filtro `layer`, porque fragmentos curtos como `"sem nota fiscal"` ficam mais próximos de um legítimo `"pode me enviar a nota fiscal da minha compra?"` (0,826) do que um ataque real fica. O `overlap_score` (Jaccard) hoje é apenas o fallback de DEMO_MODE/CI: ele não consegue separar paráfrase de pergunta legítima em nenhum limiar.

As duas primeiras camadas originais: denylist estática + checagem de near-miss (grátis). Se nada casou *e* a mensagem também não bateu numa regra de roteamento confiante (`skip_semantic` — mensagens seguras do ponto de vista de roteamento pulam inteiramente a chamada extra ao LLM, cortando custo real na Anthropic), um classificador LLM barato pega tentativas novas de manipulação e escreve um bloqueio de volta em `guardrail_denylist`, de modo que a próxima tentativa semelhante sai de graça. Um terceiro veredito, `DUVIDA` (abstenção), registra o caso incerto em `guardrail_candidates` para revisão humana, em vez de bloquear um cliente possivelmente legítimo.

**Recuperação** (`backend/app/retrieval.py`): Atlas Vector Search com Automated Embedding (`voyage-4`) sobre o catálogo de produtos, ranqueado por relevância (0,55) + avaliação (0,30) + estoque (0,15) em uma única agregação. Sobre `kb_articles` a fusão híbrida BM25+vetorial roda **server-side com `$rankFusion`** (`build_kb_rank_fusion_pipeline`, MongoDB 8.1+): uma agregação em vez de dois round-trips, e o ranking intermediário (até 40 documentos por perna) nunca trafega pela rede. `reciprocal_rank_fusion` em Python continua existindo como fallback — servidor sem `$rankFusion`, índice indisponível, ou `DEMO_MODE` sem Atlas. `search_kb` devolve `(artigos, estratégia)` e a estratégia vira o título do evento de timeline, então a demo mostra na tela qual dos dois caminhos rodou; não esconda essa distinção "simplificando" o retorno.

**Travessia de grafo** (`backend/app/graph.py`): a cadeia de trocas de um pedido (`PED-3001 → PED-3011 → PED-3021 → PED-3031`) é percorrida com `$graphLookup` sobre `orders`, seguindo `replacement_order_id → order_id`. É a única pergunta do sistema que não se responde documento a documento: o número de saltos não é conhecido de antemão, e em Python isso seria uma ida ao banco por salto (`traverse_order_chain_in_memory` é literalmente esse loop, e existe só para `DEMO_MODE`). O isolamento vale nos dois pontos: `owner_customer_key` no `$match` inicial **e** em `restrictSearchWithMatch`, para que nenhum salto alcance pedido de outro cliente por um campo mal preenchido. O sinal de negócio (`summarize_order_chain`) é aritmética sobre o array, sem LLM: três ou mais unidades do mesmo produto na cadeia é defeito de lote, não uso indevido.

**Abstração do armazenamento** (`backend/app/database.py`): o `DataStore` alterna entre o Atlas real e um backend em memória via `DEMO_MODE`, com os mesmos contratos nos dois casos — é o que permite `smoke.py`/`eval.py`/CI rodarem sem acesso a um Atlas ao vivo. `agent_handoffs`/`agent_traces` recebem um validador `$jsonSchema` (`create_schema_validators`, inócuo em `DEMO_MODE`), para que o próprio MongoDB rejeite um documento malformado, não só a camada Python.

**Transação multi-documento** (`backend/app/database.py:DataStore.transaction`): escrita de negócio e registro de decisão são **uma coisa só**. Mudar o status de um pedido e gravar a decisão que o justifica eram dois `await` em sequência; uma falha entre os dois deixava o mundo alterado sem registro — o furo que a trilha existe para impedir, aberto no meio dela. O handle devolvido é um `Transaction`, não a sessão crua do driver, porque `session is None` não conseguia distinguir "fora de transação" de "dentro, mas sem atomicidade": `Transaction.atomic` responde se um rollback é possível neste escopo, e é isso que decide entre propagar a exceção (propagar **é** o rollback) e registrar a falha sem derrubar o turno. Em `DEMO_MODE` a atomicidade é emulada por snapshot — de verdade, para o teste de rollback exercitar comportamento e não um no-op. Num mongod standalone (sem replica set) o `connect` avisa e as escritas voltam a ser sequenciais.

Conflito entre duas transações no mesmo documento vem marcado com o label `TransientTransactionError`, que significa "repita", não "falhou": `resolve_review` repete até 3 vezes (`is_transient_transaction_error`). Sem isso, dois analistas clicando no mesmo caso recebiam HTTP 500 em vez do 404 correto. Na repetição o caso já está `resolved`, o `find_one` por `status: "pending"` não acha nada, e o perdedor recebe o 404 — converge sozinho.

**Decisão e auditoria** (`backend/app/decisions.py`): separado de propósito da observabilidade. `agent_traces`/`agent_handoffs` existem para depurar e para a timeline, e expiram por TTL em 30 dias; `agent_decisions` e `agent_audit_events` são registro de conformidade e **não têm TTL**. Toda ação com efeito no mundo (mudança de status, resgate de pontos, chamado aberto, reagendamento — e também a negativa de resgate por saldo) grava um par decisão+evento via `record_decision`. `agent_decisions` é **imutável**: nunca sofre `update_one`. Corrigir uma decisão é gravar outra com `supersedes` apontando para a anterior — foi assim que a decisão humana de override ficou mensurável em vez de sobrescrever o histórico. `GET /api/decisions` devolve a trilha do próprio chamador (`customer_key` vem do JWT, nunca do query string).

**Troca como operação de domínio** (`backend/app/replacement.py`): `troca_solicitada` **não é alcançável** por `safe_order_update` — `policies.GUARDED_STATUSES` a tira do caminho genérico, e quem tentar por lá recebe um `GuardedStatusError` dizendo o que usar. O único caminho que escreve esse status é `apply_replacement`, que consulta a cadeia de reposições, decide, e só então grava (escrita + decisão na mesma transação).

Isso substituiu uma versão em que a checagem morava escrita à mão dentro dos agentes. O problema daquela versão não era teórico: bastava um caminho não lembrar da regra, e foi o que houve — o gate estava só no `warranty_agent`, que *explica* a cobertura, enquanto "quero trocar o pedido PED-0000" (a frase mais natural do cliente) ia para o `order_agent`, que *efetiva* a troca, sem passar por ele. **A regra pertence ao ponto da escrita, não ao da explicação.** Um `store.update_one` direto na collection ainda contorna tudo — nada em Python impede isso; o que mudou é que o desvio deixou de ser acidental para ser deliberado e visível numa revisão.

`warranty_agent` usa as mesmas funções em modo leitura (`assess_replacement`, `block_for_quality_review`): ele explica a cadeia e escala quando o cliente sinaliza intenção de ação (`wants_replacement`), mas nunca escreve — uma consulta passiva ("ainda tem garantia?") informa e não abre caso, senão o agente cria trabalho de analista a partir de uma pergunta.

**Escalonamento pausável** (`backend/app/reviews.py`): quando o agente encontra um caso que não deve resolver sozinho — hoje, cadeia de trocas com `needs_quality_review` — ele **para** em vez de prometer mais uma troca. A pausa é durável: mora em `pending_reviews`, não numa conexão HTTP aberta (uma requisição de chat não pode segurar o socket até um analista voltar). `open_review` é idempotente por `(subject_id, action, status)`, senão o mesmo caso empilha na fila. O analista resolve por `POST /api/admin/reviews/{id}/resolve`; a resolução grava a decisão final com `decided_by: "human"`, preserva `recommended_action`, e **devolve o caso ao agente por um handoff real** (`human_reviewer → warranty_agent`) — que é o que faz o Change Stream já existente acordar a UI do cliente ao vivo, sem canal novo. `override_rate()` mede quantas vezes o humano decidiu diferente do agente; é a métrica que justifica (ou não) afrouxar o gate depois.

**Observabilidade ao vivo**: `GET /api/events/stream` (SSE) acompanha um Change Stream em `agent_handoffs`, filtrado às conversas do próprio chamador (com fallback por polling em `DEMO_MODE`); o frontend mostra apenas o handoff mais recente e reconecta sozinho ao cair (`api.js:streamEvents`). Todo `TimelineEvent` também carrega um `op` (`read`/`write`/`vectorSearch`/`hybridSearch`/`changeStream`/`graphLookup`), renderizado como um painel de "coleções em ação" por turno e agregado em contadores cumulativos `collection.<name>.<op>` no `metrics.py` (`GET /api/metrics`).

**Prompts de demo do frontend** (`DEMOS_BY_IDENTITY` no `App.jsx`): cada entrada por identidade aciona 2+ agentes, uma escrita real ou um guardrail — nada de leituras simples de um agente só. Duas armadilhas de roteamento apareceram ao construir isso: uma palavra-chave que pertence a um agente *posterior* na cadeia pretendida (por exemplo "transportadora") pode superar a palavra-gatilho de um agente *anterior* (por exemplo "troca") no desempate por prioridade do `cheap_route` e pular o hop — formule mensagens compostas para evitar a colisão (por exemplo "entrega" em vez de "transportadora"); e a concordância de gênero em português importa nas checagens por substring ("parecida" precisa da própria entrada, não basta "parecido").

Sem containerização (nada de Dockerfile/docker-compose) — apenas desenvolvimento local, via venv + npm, com portas estritas e sem fallback para os dois serviços.

## Lacunas conhecidas (verificadas no código, não só na documentação)

- As métricas (`backend/app/metrics.py`) são apenas em processo e zeram no restart — sem persistência/agregação entre instâncias.
- Sem configuração de Docker/deploy; há CI para os testes unitários e o build de produção.
- A barreira de `troca_solicitada` é de camada de aplicação (`policies.GUARDED_STATUSES` + `replacement.apply_replacement`), não do banco. Um `store.update_one("orders", ...)` direto continua escrevendo o status sem consultar a cadeia — o MongoDB não tem como expressar "este status depende de uma travessia de grafo" num validador `$jsonSchema`, que não faz lookup entre documentos.
- A síntese por LLM e o guardrail semântico custam tokens reais da Anthropic por turno — tudo bem para uma demo, mas precisariam de ajuste de cache/amostragem antes de uso em produção de alto volume.

## Material de apoio

`docs/decks/` guarda as apresentações geradas e o PDF do template de PoV; `docs/screenshots/`, as capturas do README. Ambos são saídas/ativos, não fonte — não os trate como código.

## README e screenshots

O `README.md` é a capa pública: enquadramento curto do problema, a demo em cinco passos numerados com um screenshot cada, a tabela de agentes, stack e setup. Mantenha enxuto.

Os screenshots ficam em `docs/screenshots/`, capturados em 1600×1000 contra o cluster real. Nada precisa ser mascarado (identidades de demo semeadas), mas cada captura precisa vir de uma execução real: envie o cenário de guardrail antes de capturar a página de Guardrails (senão ela mostra um bloco JSON solitário) e rode o cenário completo de cadeia de 5 hops antes de capturar Métricas (senão todos os contadores estão zerados). Capture a timeline da cadeia a partir do topo da página, para que a faixa de "agentes em ação" e a linha de coleções em ação apareçam juntas.
