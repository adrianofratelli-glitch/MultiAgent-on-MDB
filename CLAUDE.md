# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Enterprise PoV of a multi-agent customer service system where MongoDB Atlas is both the data plane and the coordination plane. Routing rules, agent state, handoffs, memory, cache, guardrail decisions, and eval history all live in MongoDB documents and are queryable like any other operational data. See `docs/architecture.md` and `docs/adr/ADR-001-arquitetura-multi-agente.md` for the full rationale (why MongoDB over a queue/workflow engine).

8 real agents in `agent_registry`: `orchestrator`, `order_agent`, `product_agent`, `support_agent`, `billing_agent`, `warranty_agent`, `loyalty_agent`, `logistics_agent`. If the registry says N agents, N of them respond — a prior iteration padded it with ~120 inert "dormant" documents to claim "100+ agents"; that was deliberately reverted. Don't reintroduce no-op documents just to inflate a count.

Docs and UI copy are in Portuguese; code/comments are in English.

## Commands

Setup:
```bash
cp .env.example .env
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/seed.py
```

Run backend (port 8031, strict — exits if taken, no auto-fallback):
```bash
cd backend && python run.py
```

Run backend without Atlas (in-memory store, same seed data/contracts, no real Search/Vector Search/Change Streams):
```bash
cd backend && DEMO_MODE=1 AUTH_REQUIRED=1 python run.py
```

Run frontend (port 5191, strict):
```bash
cd frontend && npm install && npm run dev
```

Backend tests:
```bash
cd backend && pytest -q                                  # unit tests, full suite
cd backend && pytest tests/test_router.py -q              # single file
cd backend && pytest tests/test_router.py::test_name -q   # single test
python backend/tests/smoke.py http://127.0.0.1:8031        # black-box smoke test against a running server; nonzero exit on failure
python backend/eval.py http://127.0.0.1:8031               # golden-dataset eval (seed_data.py:EVAL_CASES), writes pass/fail history to eval_runs
cd backend && python calibrate_thresholds.py               # measures the denylist score band against labeled probes (--apply writes vector_threshold to guardrail_policies)
cd backend && python calibrate_thresholds.py --only turn --apply   # one target only; --allow-errors (turn only) writes the lowest-error threshold and lists the probes that miss
cd backend && python seed_turn_probes.py                   # explicit step: creates turn_probes + its vector index in the brain DB; deliberately NOT part of seed.py
cd backend && python seed_scope_probes.py                  # explicit step: scope_probes + scope_probes_vs (brain DB); wait READY, then:
cd backend && python calibrate_thresholds.py --only scope --apply   # measures margins on the DEV split of situations.json
cd backend && python generate_situations.py                # (re)generate tests/data/situations.json (costs a few cents of tokens)
cd backend && python eval_situations.py [--json out.json] [--compare before.json]   # measure the REAL agent on the 287 situations (dev vs holdout)
cd backend && python migrate_legacy_memory.py [--apply]   # one-off, additive/idempotent: legacy customer_memory (fact_type/value) -> fact; dry-run by default. --apply also clears the old R$350 cap
cd backend && python restore_demo_fixtures.py             # loyalty balances back to seed values (the live eval spends carla's 500 points per run)
cd backend && LIVE=1 pytest tests/test_live.py -q        # LIVE mode: real Atlas + real LLM (costs tokens; disposable customer_key, cleans up, Langfuse off). Run before shipping — DEMO_MODE hides real-driver bugs (naive datetimes, raw ObjectId, legacy docs)
```

The semantic cache **warms itself**: the server triggers `app/warmup.py` on startup and the frontend triggers it again on open (`POST /api/warmup`, single-flight, `WARMUP_COOLDOWN_MINUTES`=45 < cache TTL, `WARMUP_ON_START=0` disables). It warms generic product/support questions once per area with a neutral `warmup-<area>` identity — NOT the personal demo scenarios (orders/invoices/points), which `stable_v1` correctly never caches. A customer with an active `max_price_brl` bypasses the cache on `product_agent` turns (the cached answer ignores their limit). `python backend/warmup.py` only forces/observes it.

**Demo chips for the memory layers + cache (every user):** `app/seed_data.py:MEMORY_DEMOS` generates 6 chips per identity (`demo_kind`): ⚡ semantic cache (warmed, first click = HIT with `tokens_economizados`), 🕐 short-term 1/2 + 2/2 (question, then a rephrase in the SAME conversation → `curto_prazo` HIT; the rephrase depends on the async Atlas vector index — if it misses within seconds, click again), 🧠 long-term write / use / update (facts extracted by the LLM, budget applied as a server-side `$vectorSearch` pre-filter, then supersession). They are excluded from the golden eval (`EVAL_CASES` skips `demo_kind`; they carry state between steps). After editing them run `python backend/sync_demo_scenarios.py` (upserts only `demo_scenarios`, unlike `seed.py`). The UI button "Reiniciar memória da demo" (`POST /api/demo/reset`, JWT customer only) undoes what the demo wrote and re-activates what it superseded, so the script can be replayed. Battery: `LIVE=1 pytest tests/test_live_scenarios.py` (~6 min, all 4 users, real Atlas+LLM, restores state exactly).

`git push` runs `.githooks/pre-push` (ruff + offline tests + LIVE tests; `SKIP_LIVE=1` to skip). Activate on a fresh clone: `git config core.hooksPath .githooks`.

Backend lint (ruff configured in `pyproject.toml`, no wrapper script):
```bash
cd backend && ruff check .
```

Frontend build: `cd frontend && npm run build` (no frontend lint/test script defined).

## Architecture

**Flow:** frontend (React/Vite, `frontend/src/api.js`) → REST → backend (FastAPI, `backend/app/main.py`), JWT bearer auth via `/api/auth/token`, admin actions (toggling an agent, viewing eval history) gated by `X-Admin-Key` header.

**Orchestration** (`backend/app/orchestration.py`, `router.py`, `agents.py`): each turn passes an input guardrail, then routes via a cheap deterministic rule (`ai_brain.routing_rules`) or, only if no rule matched at all, the orchestrator LLM classifies intent. **The LLM never overrides an already-confident deterministic decision** — sampling variance made routing non-reproducible across near-identical messages when it could. `cheap_route`'s tie-break is by seeded `priority`; more specific intents (`garantia`/`fidelidade`/`logistica`) are seeded above generic ones (`status_pedido`/`fatura`) so a compound message routes to the right first agent. A turn can chain up to `MAX_HOPS = 5` agents (e.g. `support_agent` diagnoses → `product_agent` recommends → `order_agent` processes the trade, its only restricted write → `billing_agent`/`logistics_agent` confirms the follow-up); every handoff persists to `agent_handoffs`/`agent_traces` and drives the UI Timeline/Inspector. A genuinely independent compound question (order status + invoice) instead fans out `order_agent` + `billing_agent` in parallel via `asyncio.gather` (`router.py:detect_fanout`, `orchestration.py:_run_fanout`) rather than chaining — restricted to that pair on purpose, since `support_agent`/`product_agent` have a real diagnose-then-recommend dependency. Each agent's grounding instructions (`agents.py:GROUNDING_RULES`) tell it to silently ignore parts of a compound message outside its own domain rather than commenting on them — without this, agents mid-chain hallucinate policy for domains they don't own.

**Agent config is data, not code**: `ai_brain.agent_registry` holds each agent's model, persona, tools, and budget — editable at runtime with no redeploy (`AgentUpdate` model in `backend/app/models.py`).

**LLM-grounded responses** (`agents.py:llm_synthesize`): retrieval stays 100% deterministic and ownership-safe (Mongo query built in Python, never by the model), but the final sentence is generated by Anthropic over the *already-fetched* document(s) — covers arbitrary phrasing instead of only templated intents. Falls back to an f-string template when there's no API key or the call fails, so `DEMO_MODE`/CI stay deterministic.

**Write actions** (beyond `order_agent`'s status update, restricted to an approved-values allowlist): `support_agent` opens a real `support_tickets` document on explicit escalation ("atendente"/"chamado"/"escalar" — not on "no KB evidence," since the `DEMO_MODE` local-rank fallback always returns *some* article regardless of relevance); `loyalty_agent` processes a real point redemption (`$inc` on `loyalty_accounts.points`, restricted to a fixed `REWARD_CATALOG` cost table, plus a `redemptions` audit doc) or hands off to `product_agent` for "redeem points for a product"; `logistics_agent` can flag `shipments.reschedule_requested: true` (single restricted field). `order_agent`'s post-write handoff to `billing_agent`/`logistics_agent` runs regardless of whether the status *actually changed* this turn — depending on an in-turn state change meant replaying "quero trocar" after an earlier turn/eval case had already flipped the order silently dropped the handoff.

**Security model** (`backend/app/security.py`, `policies.py`, `guardrails.py`): `customer_key` comes only from the JWT, never the request payload — every query is filtered by it, filters reconstructed server-side. Conversations are bounded (20 messages / 24h TTL, resumable via `GET /api/conversations/latest`, which also replays the last turn's timeline so a resumed session doesn't look like nothing happened); audit events expire after 30 days. `budget.py` enforces per-turn token budgets (`BudgetExceeded`); `rate_limit.py` is a sliding-window limiter.

**Customer memory is LLM-extracted, server-governed** (`backend/app/memory.py`, ADR-002): a free phrase gate (`should_extract`, no regex) decides whether the turn is worth an extractor call; a cheap LLM returns third-person facts as JSON; the server then dedups by `fact_norm` against the whole active memory, supersedes contradicting facts in ONE transaction (`active: false` + `superseded_by`), and drops anything shaped like an instruction (`looks_like_instruction` — applied even when the LLM returns it). Fails closed: no LLM, malformed output, or a write failure ⇒ nothing is stored and **the turn still answers**. Budget is the structured field `max_price_brl`, injected by the server as `filter: {price: {$lte: N}}` in the catalog `$vectorSearch` (`agents.py:build_product_pipeline`) — a hard limit, never silently relaxed. `cascade_store_episode` stores only system labels (intent + agent), never the raw question/answer, and `cascade_long_term_context` only injects `kind: "episode"` docs into the prompt — raw legacy text was a persistent injection vector. Legacy `fact_type`/`value` docs are still read (`migrate_legacy_memory.py` is additive).

**A personal turn never touches the shared cache** (`cascade.py`, ADR-002), three gates cheapest-first: (1) the phrase gate — skips the cache entirely, free; (2) action request / compound message (`looks_like_action_request`, `is_compound_of`) — "abra um chamado" is not a generic question already answered, and a message far longer than the cached one is a compound request, not a paraphrase; (3) the vector classifier (`turn_classifier.py`, `$vectorSearch` on `<brain>.turn_probes`, threshold measured at 0.7162) — only on a HIT and before writing, never on a MISS. Fail-closed with granularity: no verdict discards only a **global**-scope HIT; session/customer HITs still serve, since they never leave their owner. A customer with an active `max_price_brl` also bypasses the cache on `product_agent` turns (the cached answer ignores their limit).

**Out-of-scope questions are decided by embedding, not by a word list** (`backend/app/scope_classifier.py`, ADR-004): `$vectorSearch` on `<brain>.scope_probes` (index `scope_probes_vs`) with three labels — `in` (store topic), `out` (foreign), `chat` (greeting/thanks/"quem é você?") — decided by the **margin** between the leading label and the runner-up, each label with its own measured threshold (`scope_classifier_config`, floor 0.04). Decisive `out` = polite orientation with **0 tokens**, no agent, no cache, timeline event `guardrail` with `result.out_of_scope=true` (UI card "🧭 Guardrail de escopo"), NOT treated as an attack; decisive `chat` = welcome; `in`/`unsure` go to the routing LLM (`orchestration.ROUTER_PROMPT` — describes ALL 7 agents and has the exits `conversa`/`nenhum`), so the LLM only pays where there is doubt. It runs ONLY when nothing else decided (`reaches_scope_classifier`: no strong keyword, no deterministic route, not an obvious greeting) and never drops a turn: no real verdict (DEMO_MODE, missing index, unmeasured threshold, error) ⇒ the old word-list behaviour (`router.has_domain_signal` / `has_weak_signal`). A label missing among the 12 neighbours is bounded by the LAST neighbour's score, never 0. Mixed messages answer the store part and append what was left out (`out_of_scope_sentences`; never cached).

**Security never depends on the scope classifier**: `guardrails.needs_security_review` (third-party data, fake authority, policy bypass, technical injection) forces the LLM security classifier even when a routing rule matched (a `PED-xxxx` used to skip it), and anything reaching an agent outside a keyword route passes the security classifier first. The security prompt covers *declared* intent to deceive and injection embedded in a legitimate request; per-`customer_key` isolation remains the real safety net.

**Measure with situations, not hand-written phrases** (`generate_situations.py` → `tests/data/situations.json`, 287 LLM-generated + verifier-filtered cases in 39 categories (`generate_situations.py --append` grows it without replacing measured phrases), dev/holdout split by message hash; `eval_situations.py` runs the real agent). Tune looking at `dev`; report `holdout`. Boundary categories (`expect: handled`: products the store doesn't sell, generic tech help) accept an agent's "não temos" OR the scope orientation. Baseline 87.3% (229 cases) → holdout 98.6% / dev 95.7% on the 287-case set (0% of holdout attacks reach an agent, 0% of foreign topics answered by an agent). Classification calls (security, routing, memory extractor) run at `temperature=0` — without it 2–3 attacks flipped sides between runs (`llm._request` retries without the parameter if a model rejects it). Residual: LLM non-determinism is reduced, not gone. Out-of-scope token cost is ~207 (holdout) / ~314 (dev) avg: in the ambiguous band the routing LLM now runs BEFORE the security classifier, which is skipped when routing says `nenhum`/`conversa` (canned reply) — unless the message has a suspicious shape. A generic "recomenda" alone (`has_catalog_anchor`) no longer forces the product route when the scope verdict is decisively `out`. `LIVE=1 pytest tests/test_live_random.py` + `pytest tests/test_situations_offline.py` (CI, no network).

**Guardrail vector layer is two-band** (`guardrails.check_input`): the vector index cannot separate fraud from a legitimate refund ("não recebi meu pedido, quero o dinheiro de volta" scores 0.87 against fraud phrases; several real attacks score below any cut). So it hard-blocks only at/above `vector_block_threshold` (= highest legitimate score + margin, measured by `calibrate_thresholds.py --only block --apply`; default 0.92); between `vector_threshold` and that value the message is AMBIGUOUS and the LLM classifier decides (even when routing was confident); no working classifier → allow + `guardrail_candidates` (`denylist_vetorial_ambigua`), never block a customer on vector proximity alone. Live tests must never leave learned phrases behind (`guardrail_denylist` `source=semantic_llm`) — they clean up what they taught.

**Self-reinforcing guardrail** (`guardrails.py:check_input`): three layers, cheapest first. (1) Static denylist by substring — exact phrase only. (2) **Semantic denylist via Atlas Vector Search** (`denylist_autoembed_v1` on `guardrail_denylist.phrase`, autoEmbed voyage-4, pre-filtered by `area` + `layer`): this is what blocks a *paraphrase*, deterministically and without an LLM call, and it keeps working when `skip_semantic` disables the classifier or when the message already matched a routing rule. (3) The LLM classifier below, for phrasings neither list knows yet.

Two invariants here, both learned by measurement (`backend/calibrate_thresholds.py`): the `vector_threshold` in `guardrail_policies` is **measured against paraphrase probes, never guessed** — calibrating with near-copies of the seeded phrase pins it to the "identical text" band and reverts the guardrail to exact-match-only; and the lexical entries are excluded from the vector index via the `layer` filter, because short fragments like `"sem nota fiscal"` sit closer to a legitimate `"pode me enviar a nota fiscal da minha compra?"` (0.826) than a real attack does. `overlap_score` (Jaccard) is now only the DEMO_MODE/CI fallback: it cannot separate paraphrase from legitimate question at any threshold.

The original first two layers: static denylist + near-miss check (free). If nothing matched *and* the message didn't already hit a confident routing rule (`skip_semantic` — routing-safe messages skip the extra LLM call entirely, cutting real Anthropic cost), a cheap LLM classifier catches novel manipulation attempts and writes a block back into `guardrail_denylist` so the next similar attempt is free. A third verdict, `DUVIDA` (abstention), logs an uncertain case to `guardrail_candidates` for human review instead of blocking a possibly-legitimate customer.

**Retrieval** (`backend/app/retrieval.py`): Atlas Vector Search with Automated Embedding (`voyage-4`) over the product catalog, ranked by relevance (0.55) + rating (0.30) + stock (0.15) in one aggregation; hybrid BM25+vector RRF over `kb_articles`.

**Data store abstraction** (`backend/app/database.py`): `DataStore` toggles between real Atlas and an in-memory backend via `DEMO_MODE`, same contracts either way — what lets `smoke.py`/`eval.py`/CI run without live Atlas access. `agent_handoffs`/`agent_traces` get a `$jsonSchema` validator (`create_schema_validators`, no-op in `DEMO_MODE`) so MongoDB itself rejects a malformed document, not just the Python layer.

**Live observability**: `GET /api/events/stream` (SSE) tails a Change Stream on `agent_handoffs`, filtered to the caller's own conversations (poll fallback in `DEMO_MODE`); the frontend shows only the latest handoff, reconnecting automatically on drop (`api.js:streamEvents`). Every `TimelineEvent` also carries an `op` (`read`/`write`/`vectorSearch`/`hybridSearch`/`changeStream`), rendered as a per-turn "collections in action" panel and rolled into cumulative `collection.<name>.<op>` counters in `metrics.py` (`GET /api/metrics`).

**Frontend demo prompts** (`DEMOS_BY_IDENTITY` in `App.jsx`): every entry per identity triggers 2+ agents, a real write, or a guardrail — no plain single-agent reads. Two routing gotchas surfaced building these: a keyword belonging to a *later* agent in an intended chain (e.g. "transportadora") can outrank an *earlier* agent's trigger word (e.g. "troca") in `cheap_route`'s priority tie-break and skip the hop — phrase compound messages to avoid the collision (e.g. "entrega" instead of "transportadora"); Portuguese gender agreement matters for substring keyword checks ("parecida" needs its own entry, not just "parecido").

No containerization (no Dockerfile/docker-compose) — local dev only, via venv + npm, with strict non-fallback ports for both services.

## Known gaps (verified against code, not just docs)

- Metrics (`backend/app/metrics.py`) are in-process only, reset on restart — no persistence/aggregation across instances.
- CI runs backend tests and lint plus a clean frontend build. There is no Docker or deployment configuration.
- LLM synthesis and the semantic guardrail both cost real Anthropic tokens per turn — fine for a demo, would need caching/sampling tuning before high-volume production use.


## Estado atual e verificação

`main` está publicado (ver `git log`; ADR-004 documenta a última rodada). Suíte offline verde (402, sem rede), eval dourado **29/29 em modo LIVE**, baterias live dos 4 clientes e de perguntas aleatórias verdes. Não refaça as decisões já registradas nos ADRs 002/003 — elas vieram de medição contra o cluster, não de preferência.

`git push` roda `.githooks/pre-push` (ruff + pytest offline + `tests/test_live.py`); `SKIP_LIVE=1` pula a parte live. Num clone novo: `git config core.hooksPath .githooks`.

Antes de uma demo/eval que gasta estado: `python backend/restore_demo_fixtures.py` (o eval consome 500 pontos da carla por rodada). Depois de mexer em `DEMO_SCENARIOS`: `python backend/sync_demo_scenarios.py`.

**O que vive no cluster Atlas (NÃO está no git — não refaça, verifique):** brain DB `multiagent_brain`: `turn_probes` (44) + índice `turn_probes_vs` + `turn_classifier_config` (limiar 0,7162); `scope_probes` (214) + índice `scope_probes_vs` + `scope_classifier_config` (margens 0,04/0,04/0,04); `guardrail_policies.vector_block_threshold` = 0,8814; `demo_scenarios` (53 roteiros, via `sync_demo_scenarios.py`). Main DB: `customer_memory` legado migrado por `migrate_legacy_memory.py` (aditivo; teto de R$ 350 removido). Adicionar probes reindexa de forma assíncrona (minutos); recalibre só depois de o probe novo ser o vizinho nº 1 dele mesmo. **O cluster precisa estar ligado**: o hook `pre-push` e todas as suítes live dependem dele (já esteve pausado uma vez e o push falhou).

**Pendências conhecidas (não são bugs novos):** "escreva um poema sobre X" às vezes vira boas-vindas (o LLM de roteamento diz `conversa`); recomendação alheia dentro de mensagem longa com saudação pode cair na faixa ambígua e ir ao `product_agent` (2 casos no dev); ~2–3 ataques oscilam por ser LLM (mesmo com `temperature=0`); o conjunto é gerado por LLM — falhas de tráfego real devem entrar nele. Próximo passo natural: alimentar `situations.json` com falhas reais e recalibrar (`--only scope`).

Regressões de frontend: `cd frontend && node --test tests/*.test.mjs`. No workspace, `../STATUS_PORTFOLIO.md` aponta para as evidências e decisões restantes. Não faça push nem altere dataset/schema/core sem autorização específica.

## Observability (Langfuse)

`app/langfuse_client.py:build_turn_trace` manda UMA trace por turno cobrindo a `timeline` inteira — roteamento, decisão de cache, cada hop de agente (generation) e handoff/guardrail (span) — chamada de dentro de `orchestration.py:_persist_trace`, o único ponto de saída de todo turno (6 caminhos: bloqueio, fora de escopo, cache hit em `run_turn`/`_run_fanout`, cadeia completa, fanout completo). Fail-open sem `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`/`langfuse_enabled` — nunca derruba o turno; `get_langfuse()` roda `auth_check()` uma vez por processo para nunca expor um link que dá 404. `message`/`response` chegam já mascarados pelo guardrail de PII antes de qualquer chamada ao Langfuse. O card "💰 Economia MongoDB" no frontend (`App.jsx`) mostra cascata semântica + prompt cache do turno sem precisar abrir o Langfuse.

**Nunca mencionar Postgres em call/demo/material de cliente** — é infra interna do Langfuse (self-host), invisível, e citá-la mistura a mensagem com um concorrente direto da MongoDB. Ver `../observability/README.md` para o racional completo.
