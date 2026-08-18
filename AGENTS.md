# AGENTS.md

Este arquivo orienta o Codex (Codex.ai/code) ao trabalhar com o código deste repositório.

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
python backend/seed.py
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
```

Antes de uma demo ao vivo, pré-aqueça o cache semântico para que o primeiro clique do cliente não seja uma cadeia multi-hop fria de LLM:
```bash
python backend/warmup.py http://127.0.0.1:8031
```
Isso chama de verdade, contra a Anthropic, cada prompt de demo que não seja de guardrail (espelhando `frontend/src/App.jsx:DEMOS_BY_IDENTITY` literalmente — a chave de cache é a mensagem normalizada), uma vez por identidade. É pré-aquecimento honesto, não uso fabricado: o primeiro turno real já aconteceu durante o warmup, então o clique ao vivo é um `cache_hit: true` genuíno reproduzindo a timeline armazenada por inteiro. O TTL do `semantic_cache` é de 60 minutos, para sobreviver ao trajeto entre o warmup e a reunião.

Lint do backend (ruff configurado no `pyproject.toml`, sem script wrapper):
```bash
cd backend && ruff check .
```

Build do frontend: `cd frontend && npm run build` (não há script de lint/test no frontend).

## Arquitetura

**Fluxo:** frontend (React/Vite, `frontend/src/api.js`) → REST → backend (FastAPI, `backend/app/main.py`), autenticação JWT bearer via `/api/auth/token`, ações administrativas (ligar/desligar um agente, ver histórico de eval) protegidas pelo cabeçalho `X-Admin-Key`.

**Orquestração** (`backend/app/orchestration.py`, `router.py`, `agents.py`): cada turno passa por um guardrail de entrada e então é roteado por uma regra determinística barata (`multiagent_brain.routing_rules`) ou, apenas se nenhuma regra casar, o LLM orquestrador classifica a intenção. **O LLM nunca sobrepõe uma decisão determinística já confiante** — quando podia, a variância de amostragem tornava o roteamento não reprodutível entre mensagens quase idênticas. O desempate do `cheap_route` é pelo `priority` semeado; intenções mais específicas (`garantia`/`fidelidade`/`logistica`) são semeadas acima das genéricas (`status_pedido`/`fatura`), para que uma mensagem composta caia no primeiro agente certo. Um turno pode encadear até `MAX_HOPS = 4` agentes (por exemplo `support_agent` diagnostica → `product_agent` recomenda → `order_agent` processa a troca, sua única escrita restrita → `billing_agent`/`logistics_agent` confirma o desdobramento); cada handoff é persistido em `agent_handoffs`/`agent_traces` e alimenta o Timeline/Inspector da UI. Já uma pergunta composta genuinamente independente (status do pedido + fatura) faz fan-out de `order_agent` + `billing_agent` em paralelo via `asyncio.gather` (`router.py:detect_fanout`, `orchestration.py:_run_fanout`) em vez de encadear — restrito a esse par de propósito, já que `support_agent`/`product_agent` têm uma dependência real de diagnosticar-e-então-recomendar. As instruções de grounding de cada agente (`agents.py:GROUNDING_RULES`) mandam ignorar silenciosamente as partes de uma mensagem composta fora do próprio domínio, em vez de comentá-las — sem isso, agentes no meio da cadeia alucinam políticas de domínios que não são deles.

**Configuração de agente é dado, não código**: `multiagent_brain.agent_registry` guarda o modelo, a persona, as ferramentas e o orçamento de cada agente — editáveis em tempo de execução sem redeploy (modelo `AgentUpdate` em `backend/app/models.py`).

**Respostas ancoradas por LLM** (`agents.py:llm_synthesize`): a recuperação continua 100% determinística e segura quanto a propriedade do dado (query Mongo construída em Python, nunca pelo modelo), mas a frase final é gerada pela Anthropic sobre o(s) documento(s) *já recuperado(s)* — o que cobre formulações arbitrárias, e não apenas intenções templadas. Cai para um template de f-string quando não há chave de API ou a chamada falha, de modo que `DEMO_MODE`/CI seguem determinísticos.

**Ações de escrita** (além da atualização de status do `order_agent`, restrita a uma allowlist de valores aprovados): o `support_agent` abre um documento real em `support_tickets` em caso de escalonamento explícito ("atendente"/"chamado"/"escalar" — e não por "sem evidência na KB", já que o fallback de ranking local do `DEMO_MODE` sempre devolve *algum* artigo, relevante ou não); o `loyalty_agent` processa um resgate real de pontos (`$inc` em `loyalty_accounts.points`, restrito a uma tabela fixa de custos `REWARD_CATALOG`, mais um documento de auditoria em `redemptions`) ou faz handoff para o `product_agent` no caso de "resgatar pontos por um produto"; o `logistics_agent` pode marcar `shipments.reschedule_requested: true` (um único campo restrito). O handoff pós-escrita do `order_agent` para `billing_agent`/`logistics_agent` roda independentemente de o status ter *de fato mudado* neste turno — depender de uma mudança de estado no turno fazia com que repetir "quero trocar" depois de um turno/caso de eval anterior já ter virado o pedido derrubasse o handoff em silêncio.

**Modelo de segurança** (`backend/app/security.py`, `policies.py`, `guardrails.py`): a `customer_key` vem apenas do JWT, nunca do payload da requisição — toda query é filtrada por ela, com os filtros reconstruídos no servidor. As conversas são limitadas (20 mensagens / TTL de 24h, retomáveis via `GET /api/conversations/latest`, que também reproduz a timeline do último turno para que uma sessão retomada não pareça vazia); eventos de auditoria expiram em 30 dias. O `budget.py` aplica orçamentos de token por turno (`BudgetExceeded`); o `rate_limit.py` é um limitador de janela deslizante.

**Guardrail auto-reforçado** (`guardrails.py:check_input`): primeiro a denylist estática + a checagem de near-miss (grátis). Se nada casou *e* a mensagem também não bateu numa regra de roteamento confiante (`skip_semantic` — mensagens seguras do ponto de vista de roteamento pulam inteiramente a chamada extra ao LLM, cortando custo real na Anthropic), um classificador LLM barato pega tentativas novas de manipulação e escreve um bloqueio de volta em `guardrail_denylist`, de modo que a próxima tentativa semelhante sai de graça. Um terceiro veredito, `DUVIDA` (abstenção), registra o caso incerto em `guardrail_candidates` para revisão humana, em vez de bloquear um cliente possivelmente legítimo.

**Recuperação** (`backend/app/retrieval.py`): Atlas Vector Search com Automated Embedding (`voyage-4`) sobre o catálogo de produtos, ranqueado por relevância (0,55) + avaliação (0,30) + estoque (0,15) em uma única agregação; RRF híbrido BM25+vetorial sobre `kb_articles`.

**Abstração do armazenamento** (`backend/app/database.py`): o `DataStore` alterna entre o Atlas real e um backend em memória via `DEMO_MODE`, com os mesmos contratos nos dois casos — é o que permite `smoke.py`/`eval.py`/CI rodarem sem acesso a um Atlas ao vivo. `agent_handoffs`/`agent_traces` recebem um validador `$jsonSchema` (`create_schema_validators`, inócuo em `DEMO_MODE`), para que o próprio MongoDB rejeite um documento malformado, não só a camada Python.

**Observabilidade ao vivo**: `GET /api/events/stream` (SSE) acompanha um Change Stream em `agent_handoffs`, filtrado às conversas do próprio chamador (com fallback por polling em `DEMO_MODE`); o frontend mostra apenas o handoff mais recente e reconecta sozinho ao cair (`api.js:streamEvents`). Todo `TimelineEvent` também carrega um `op` (`read`/`write`/`vectorSearch`/`hybridSearch`/`changeStream`), renderizado como um painel de "coleções em ação" por turno e agregado em contadores cumulativos `collection.<name>.<op>` no `metrics.py` (`GET /api/metrics`).

**Prompts de demo do frontend** (`DEMOS_BY_IDENTITY` no `App.jsx`): cada entrada por identidade aciona 2+ agentes, uma escrita real ou um guardrail — nada de leituras simples de um agente só. Duas armadilhas de roteamento apareceram ao construir isso: uma palavra-chave que pertence a um agente *posterior* na cadeia pretendida (por exemplo "transportadora") pode superar a palavra-gatilho de um agente *anterior* (por exemplo "troca") no desempate por prioridade do `cheap_route` e pular o hop — formule mensagens compostas para evitar a colisão (por exemplo "entrega" em vez de "transportadora"); e a concordância de gênero em português importa nas checagens por substring ("parecida" precisa da própria entrada, não basta "parecido").

Sem containerização (nada de Dockerfile/docker-compose) — apenas desenvolvimento local, via venv + npm, com portas estritas e sem fallback para os dois serviços.

## Lacunas conhecidas (verificadas no código, não só na documentação)

- As métricas (`backend/app/metrics.py`) são apenas em processo e zeram no restart — sem persistência/agregação entre instâncias.
- Sem configuração de CI/Docker/deploy.
- A síntese por LLM e o guardrail semântico custam tokens reais da Anthropic por turno — tudo bem para uma demo, mas precisariam de ajuste de cache/amostragem antes de uso em produção de alto volume.
