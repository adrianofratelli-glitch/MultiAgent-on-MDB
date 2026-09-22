# Multi-agente no MongoDB

[![CI](https://github.com/adrianofratelli-glitch/MultiAgent-on-MDB/actions/workflows/ci.yml/badge.svg)](https://github.com/adrianofratelli-glitch/MultiAgent-on-MDB/actions/workflows/ci.yml)

8 agentes de atendimento que se coordenam pelo MongoDB Atlas — sem fila, sem Redis, sem banco vetorial separado. Regras de roteamento, configurações dos agentes, memória, cache, handoffs e decisões de guardrail são todos documentos que você pode consultar enquanto a conversa acontece.

## A demo em 5 passos

**1. O cliente manda uma única mensagem.**

![Tela inicial do chat com os prompts de demonstração](docs/screenshots/01-chat-home.png)

**2. Ela percorre 4 agentes em um só turno.** Suporte diagnostica o defeito → produto recomenda um item mais barato → pedidos processa a troca (a única escrita) → faturamento explica o impacto na fatura. Cada hop é um documento em `agent_handoffs`, transmitido ao vivo por Change Streams.

![Timeline da cadeia de agentes mostrando quatro handoffs em um único turno](docs/screenshots/03-chain-timeline.png)

**3. Agentes são dados, não deploys.** Modelo, persona, ferramentas e orçamento de tokens vivem no `agent_registry` — ligue/desligue um agente ou troque o modelo dele no meio da demo, sem redeploy.

![Registry de agentes com modelo, escopo e chave liga/desliga por agente](docs/screenshots/04-agents-registry.png)

**4. Tente quebrar — inclusive com pergunta aleatória.** Um jailbreak ou um prompt de falsa autoridade bate primeiro na denylist; o que for novo vai para um classificador LLM barato que escreve o padrão de volta na denylist, então a próxima tentativa sai de graça. O corte de bloqueio automático é **medido**, não chutado: o vetor não separa fraude de reembolso legítimo ("não recebi meu pedido, quero o dinheiro de volta" pontua 0,8664 contra uma frase de fraude), então acima do maior score legítimo medido ele bloqueia sozinho e na faixa ambígua quem decide é o classificador — cliente nunca é barrado por vizinhança vetorial. E "qual é a temperatura hoje?" não é ataque: recebe orientação educada com **0 tokens**, sem agente e sem cache, marcada como `🧭 Guardrail de escopo`. Quem decide o que é da loja não é uma lista de palavras: é uma busca vetorial (`scope_probes`) que entende inglês, gíria e erro de digitação, e só chama o LLM na faixa ambígua. Medido em **287 situações geradas por LLM** (com holdout): acerto **87,3% → 98,6%** no holdout, 0% de cliente legítimo bloqueado.

![Painel de guardrails: bloqueios, denylist auto-alimentada, casos ambíguos sinalizados](docs/screenshots/06-guardrails.png)

**5. Prove que aconteceu.** As métricas vêm das mesmas coleções em que todo o resto escreve.

![Métricas: cobertura de agentes, handoffs, escritas, buscas nativas](docs/screenshots/05-metrics.png)

## Os agentes

| Agente | Função | Escreve? |
|---|---|---|
| `orchestrator` | Classifica a intenção e roteia | Não |
| `order_agent` | Status do pedido, trocas/reembolsos | Sim — só status, com valores aprovados |
| `product_agent` | Recomendações de catálogo via `$vectorSearch` | Não |
| `support_agent` | Diagnóstico via RAG híbrido, abre chamados | Sim — tickets de suporte |
| `billing_agent` | Consulta de faturas | Não |
| `warranty_agent` | Cobertura por categoria + data da compra | Não |
| `loyalty_agent` | Pontos, tiers, resgate de recompensas | Sim — dedução de pontos |
| `logistics_agent` | Transportadora, rastreio, previsão de entrega | Sim — flag de reagendamento |

## Stack

Python 3.12 · FastAPI · React + Vite · Anthropic (Haiku para roteamento, Sonnet para raciocínio) · MongoDB Atlas (Vector Search com auto-embedding `voyage-4`, RRF híbrido, Change Streams, TTL, validação de schema).

## Como rodar

```bash
cp .env.example .env
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/seed.py
./start.sh                      # backend :8031 + frontend :5191
```

O launcher usa backend sem reload e build otimizado do frontend por padrão. Para desenvolver com reload/HMR, rode `POV_DEV=1 ./start.sh`; o build só é refeito quando fontes, lockfile ou configuração mudam.

Sem cluster Atlas? `DEMO_MODE=1 AUTH_REQUIRED=1 python run.py` roda os mesmos contratos em memória (sem Vector Search / Change Streams). É o que a CI usa.

**O cache se aquece sozinho.** O servidor dispara o warmup ao subir e o frontend dispara de novo ao abrir (`POST /api/warmup`, execução única por vez, no máximo uma a cada 45 min) — o primeiro clique numa pergunta genérica já é `cache_hit: true`. Nada de lembrar de rodar script antes da call; `python backend/warmup.py` só força e acompanha.

A demo escreve de verdade (fatos, episódios, cache do cliente). O botão **"Reiniciar memória da demo"** (`POST /api/demo/reset`, só o cliente do JWT) desfaz o que ela gravou e reativa o que ela substituiu, para repetir o roteiro do zero.

## Testes

```bash
cd backend
pytest -q                       # unitários (408, sem rede)
python tests/smoke.py <url>     # caixa-preta
python eval.py <url>            # golden dataset, resultados em eval_runs

# modo LIVE — Atlas e LLM REAIS (custa tokens; identidade descartável, limpa o que gravou)
LIVE=1 pytest tests/test_live.py -q            # ~2 min — contratos essenciais
LIVE=1 pytest tests/test_live_random.py -q     # ~4 min — perguntas aleatórias e fora de escopo
LIVE=1 pytest tests/test_live_scenarios.py -q  # ~10 min — jornada completa dos 4 clientes
python eval_situations.py                      # ~7 min — 287 situações geradas por LLM contra o agente real (dev vs holdout)
```

`DEMO_MODE` esconde bugs que só o driver real produz — datetime sem fuso, `ObjectId` cru na timeline, documento legado sem o campo novo. Os três foram encontrados exatamente assim, em modo LIVE, depois de a suíte offline estar verde. Por isso `git push` roda `.githooks/pre-push` (ruff + testes offline + `test_live.py`); ative num clone novo com `git config core.hooksPath .githooks`.

O smoke repete a consulta personalizada dentro do mesmo `conversation_id` e
exige HIT em `short_term_memory`; em seguida abre uma conversa nova e exige
MISS. Assim ele valida o cache sem transformar replay de estado operacional em
vazamento entre sessões.

Todo pull request roda a suíte de testes do backend e checagens do Ruff, além
de um build de produção limpo do frontend e auditoria de dependências. A CI
usa a implementação determinística de data-store em memória e não exige
credenciais de Atlas ou Anthropic.

## Fluxo de um turno

```
cliente ──> POST /api/chat (JWT)
             │
             ├─ guardrail de entrada  (denylist lexical -> vetorial -> classificador LLM)
             ├─ escopo por embedding  (in / out / chat)  ── out/chat ──> orientação, 0 token
             ├─ roteamento            (regra determinística -> LLM só na dúvida)
             ├─ cascata semântica     (curto prazo -> cache global)  ── HIT ──> resposta cacheada
             │
             ▼
        SUPERVISOR  (teto de 5 hops, timeout por agente, detector de laço)
             │
             ├── fan-out paralelo ──> order_agent ║ billing_agent
             └── cadeia ──> support_agent ─handoff─> product_agent ─handoff─> order_agent ─> logistics/billing
                                 │                       │                       │
                                 └── tools (Atlas): find / vectorSearch / hybridSearch / write
             │
             ├─ guardrail de saída + memória (fato, episódio, cache)
             └─ trace do turno (Langfuse) + spans OpenTelemetry (agente, handoff, tool, LLM)
```

Cada agente, handoff, tool e chamada de LLM vira um span com `conversation_id`, agente, tokens,
custo estimado e latência — é o que `backend/scripts/trace_query.py` usa para responder **quem
travou e onde**:

```bash
cd backend && TRACE_SINK=atlas ../.venv/bin/python run.py      # spans viram documentos no Atlas
cd backend && ../.venv/bin/python scripts/trace_query.py       # ranking por conversa
conversa               spans erros  tokens  custo_usd  mais lento
conv-8b3ca34a297a         20     2       0    0.00000  agent [order_agent] 3ms  ERRO em tool.orders.find_many
```

## Flags (tudo opt-in; sem nenhuma delas o comportamento é o de sempre)

| Flag | Default | O que liga |
|---|---|---|
| `TRACE_SINK` | `off` | tracing OpenTelemetry: `console`, `phoenix` ou `atlas` (spans viram documentos) |
| `TRACE_MASK_PII` | forçado a `1` | com qualquer sink ligado, o conteúdo dos spans é mascarado — não é opcional |
| `SUPERVISOR_LEGACY_500` | `0` | **volta** o comportamento antigo: falha de agente sobe como 500. A degradação graciosa é o padrão |
| `AGENT_TIMEOUT_SECONDS` | `45` | teto por hop de agente (sempre ativo) |
| `LOOP_GUARD_REPEATS` | `2` | repetições de (agente, intenção) antes de escalar para humano |
| `TOOL_TIMEOUT_SECONDS` | `0` (desligado) | teto por chamada de tool, inclusive fora do hop de agente |
| `TOOL_BREAKER` | `1` (ligado) | circuit breaker por tool: 4 falhas **consecutivas** abrem por 30s; `0` desliga |
| `MONGODB_TEST_DB` / `MONGODB_TEST_BRAIN_DB` | `<banco>_test` | bancos isolados usados pelos scripts que escrevem dado real |
| `ALLOW_DEMO_DB_WRITE` | `0` | escape hatch: deixa esses scripts escreverem no banco da demo |
| `GUARDRAILS_EDGE` | `0` | `mask_pii` nos logs e `validate_output` (`max_repairs=0`) na resposta, via `_shared` |
| `CHAOS` | `0` | habilita os pontos de injeção de falha (`CHAOS_SCENARIO`, `CHAOS_TARGET`, `CHAOS_PHASE`, `CHAOS_STATUS`, `CHAOS_DELAY`, `CHAOS_COUNT`) |

O gateway de LLM (`app/llm.py`) já tinha retry com backoff, fallback de modelo e circuit breaker
por endpoint — isso continua ligado por padrão, como sempre esteve.

**A PoV é resiliente por padrão:** degradação graciosa do supervisor, timeout por agente,
detector de laço e circuit breaker por tool valem sem ligar nada. As flags acima existem para
DESLIGAR (`SUPERVISOR_LEGACY_500`, `TOOL_BREAKER=0`) ou para ajustar limite — não para ligar a
resiliência. A suíte offline continua 402/402 idêntica ao baseline nos dois modos.

## Resiliência (medida, não afirmada)

`backend/scripts/chaos_suite.py` é o PoV tentando se quebrar sozinho: 10 cenários de falha
injetada no caminho real, cada um com uma assertion explícita do que "resiliente" significa ali.
Última execução: **11/11**. Os mesmos cenários rodam como regressão em `tests/test_chaos.py`.

```bash
cd backend && CHAOS=1 ../.venv/bin/python scripts/chaos_suite.py          # bateria toda
cd backend && CHAOS=1 LIVE=1 ../.venv/bin/python scripts/chaos_suite.py   # inclui o SIGKILL (Atlas real)
cd backend && CHAOS=1 ../.venv/bin/python -m pytest tests/test_chaos.py -q
```

**O que quebrava antes e foi corrigido por causa da bateria:**

* O timeout do supervisor só cobria o que acontece dentro de um hop. Uma consulta pendurada no
  carregamento do turno segurava tudo por 20s com `AGENT_TIMEOUT_SECONDS=1`. Agora existe teto
  por tool (`TOOL_TIMEOUT_SECONDS`) na fronteira única de acesso ao Atlas: 21,2s -> 2,2s.
* Falha de tool não contava para o circuit breaker (o ponto de falha estava fora do bloco
  protegido): 5 turnos de erro seguidos deixavam o contador em zero.
* O cenário de "agente travado" não interrompia nada — medir isso foi o que mostrou que o ponto
  de falha precisava estar dentro da corrotina cronometrada.

**Isolamento de banco:** os cenários que escrevem dado real (`crash_resume`) e o
`eval_routing.py --live` usam bancos de teste isolados no mesmo cluster
(`multi_agent_poc_test` / `multiagent_brain_test`, `backend/scripts/isolation.py`) e **recusam
rodar** se o destino for o banco da demo, a menos que `ALLOW_DEMO_DB_WRITE=1` seja passado. O
primeiro uso provisiona o banco de teste (seed + índices Search/Vector reais, alguns minutos):
`cd backend && ../.venv/bin/python scripts/isolation.py`. Como nada disso toca a demo,
`restore_demo_fixtures.py` deixou de ser parte do fluxo normal — ficou como recurso de
emergência, para quem rodar algo fora do padrão (ou com `ALLOW_DEMO_DB_WRITE=1`).

**Limitações conhecidas:** não há streaming (o cenário de falha "no meio do stream" é a queda
logo depois da resposta do provedor); a concorrência foi medida com 5 requests simultâneos em
processo único, não é teste de carga; o banco de teste não tem `turn_probes`/`scope_probes`, então
lá os classificadores por embedding caem no fallback documentado por palavras.
Detalhes e números em [docs/chaos-report.md](docs/chaos-report.md).

## Eval comparável com o singleagent

24 conversas de referência com roteamento esperado (`eval/routing_dataset.json`, `synthetic: true`)
e as métricas que as duas PoVs conseguem medir: acurácia de roteamento (agente de **entrada**),
taxa de resolução, handoffs por turno e tokens por turno. Formato documentado em
[eval/FORMAT.md](eval/FORMAT.md) para o singleagent reaproveitar.

```bash
cd backend && ../.venv/bin/python eval_routing.py           # offline: 100% rota, 100% resolução, 0,125 handoff/turno, 43,5 tokens
cd backend && ../.venv/bin/python eval_routing.py --live    # Atlas + LLM, banco ISOLADO: 100% / 100% / 0,125 / 855,5 tokens
```

O dataset é sintético e da mesma família de modelo do agente: serve como regressão, não como
estimativa de tráfego real. Três casos só têm veredito com LLM e ficam fora da acurácia offline.

## Observability opcional: Langfuse

Com `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` no `.env` (`backend/app/langfuse_client.py`), cada turno vira UMA trace cobrindo a timeline inteira — roteamento, decisão de cache e cada hop de agente com seu handoff, não só um número de cache hit-rate isolado. Cada agente que respondeu vira uma generation; cache/handoff/memória/guardrail viram spans. Fail-open: sem as chaves, ou com o Langfuse fora do ar, vira no-op (`auth_check()` roda uma vez por processo, então um Langfuse indisponível nunca expõe um link que dê 404 no meio de uma demo). Badge "Ver trace no Langfuse" e card "Economia MongoDB" (cascata semântica + prompt cache) aparecem no cabeçalho do turno, na própria UI.

## Fronteira de produção

Defina `ENVIRONMENT=production`, `AUTH_REQUIRED=1` e `DEMO_TOKEN_ISSUANCE_ENABLED=0`. A inicialização então falha fechada em caso de segredo de JWT/admin fraco ou padrão, CORS com curinga, autenticação desabilitada ou emissão de token de demo ligada. O `/metrics` é só para admin. O lançador local continua sendo um runtime de PoV; adicione terminação TLS, um IdP corporativo e uma plataforma gerenciada de processos/containers antes de qualquer exposição externa.

## Documentação

[Arquitetura](docs/architecture.md) · [ADR-001 — coordenação orientada a documentos](docs/adr/ADR-001-arquitetura-multi-agente.md) · [ADR-002 — memória por LLM e turno pessoal fora do cache](docs/adr/ADR-002-memoria-llm-e-turno-pessoal.md) · [ADR-003 — guardrail em duas faixas e fora de escopo](docs/adr/ADR-003-guardrail-em-duas-faixas.md) · [ADR-004 — escopo por embedding e medição por situações](docs/adr/ADR-004-escopo-por-embedding-e-medicao-por-situacoes.md) · [Relatório de caos](docs/chaos-report.md) · [Formato do eval](eval/FORMAT.md) · [Atritos com o _shared](docs/shared-feedback.md)
