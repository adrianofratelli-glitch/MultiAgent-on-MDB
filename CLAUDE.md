# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Enterprise PoV of a multi-agent customer service system where MongoDB Atlas is both the data plane and the coordination plane. Routing rules, agent state, handoffs and audit traces all live in MongoDB documents and are queryable like any other operational data. See `docs/architecture.md` and `docs/adr/ADR-001-arquitetura-multi-agente.md` for the full rationale (why MongoDB over a queue/workflow engine).

8 real agents in `agent_registry`: `orchestrator`, `order_agent`, `product_agent`, `support_agent`, `billing_agent`, `warranty_agent`, `loyalty_agent`, `logistics_agent`. (A prior iteration padded the registry with ~120 "dormant" no-op agent documents to claim "100+ agents" — deliberately reverted. If the registry says N agents, N of them respond; don't reintroduce inert documents just to inflate a count.)

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

Run backend without Atlas (in-memory store, same seed data/contracts, no real Search/Vector Search):
```bash
cd backend && DEMO_MODE=1 AUTH_REQUIRED=1 python run.py
```

Run frontend (port 5191, strict):
```bash
cd frontend && npm install && npm run dev
```

Backend tests:
```bash
cd backend && pytest -q                                  # full suite
cd backend && pytest tests/test_router.py -q              # single file
cd backend && pytest tests/test_router.py::test_name -q   # single test
python backend/tests/smoke.py http://127.0.0.1:8031        # black-box smoke test (health, auth, order flow, handoff, tenant isolation, cache, metrics); nonzero exit on failure
```

Backend lint (ruff configured in `pyproject.toml`, no wrapper script):
```bash
cd backend && ruff check .
```

Frontend build: `cd frontend && npm run build` (no frontend lint/test script defined).

## Architecture

**Flow:** frontend (React/Vite, `frontend/src/api.js`) → REST → backend (FastAPI, `backend/app/main.py`), JWT bearer auth via `/api/auth/token`, admin actions (e.g. toggling an agent) gated by `X-Admin-Key` header.

**Orchestration** (`backend/app/orchestration.py`, `router.py`, `agents.py`): each turn passes an input guardrail, then either a cheap deterministic local rule (`ai_brain.routing_rules`) or the orchestrator LLM (Anthropic, for ambiguous intent) picks an agent among `order_agent`, `product_agent`, `support_agent`, `billing_agent`. The LLM classification is only consulted when `deterministic_orchestrator` found nothing at all (`decision.source == "fallback"`) — if a keyword like "defeito" already gave a confident deterministic decision, that decision is *not* overridden by the LLM, since sampling variance made routing non-reproducible across otherwise-identical messages. A chain can go up to `MAX_HOPS = 4` agents in one turn (e.g. `support_agent` diagnoses → `product_agent` recommends → `order_agent` processes the trade write → `billing_agent` confirms invoice impact); every handoff is persisted to `agent_handoffs`/`agent_traces`, driving the UI Timeline/Inspector components. Each agent's grounding instructions (`agents.py:GROUNDING_RULES`) tell it to silently ignore parts of a compound message outside its own domain rather than commenting on or apologizing for them — without this, agents mid-chain would hallucinate policy for domains they don't own.

**Agent config is data, not code**: `ai_brain.agent_registry` holds each agent's model, tools, and budget — editable at runtime with no redeploy (see `AgentUpdate` model in `backend/app/models.py`).

**Security model** (`backend/app/security.py`, `policies.py`, `guardrails.py`): `customer_key` is derived only from the JWT, never trusted from request payloads — every order/invoice query is filtered by it. Only `order_agent` holds a write tool, and it's restricted to `$set.status`. Conversations are bounded (20 messages / 24h TTL, resumable via `GET /api/conversations/latest`, which also replays the last turn's timeline so a resumed session doesn't look like the multi-agent chain never ran); audit events expire after 30 days. `budget.py` enforces a per-turn token budget (`BudgetExceeded`); `rate_limit.py` is a sliding-window limiter.

**Retrieval** (`backend/app/retrieval.py`): Atlas Vector Search with Automated Embedding (`voyage-4`) over the product catalog; hybrid BM25+vector RRF over `kb_articles` for support knowledge.

**Data store abstraction** (`backend/app/database.py`): `DataStore` toggles between real Atlas and an in-memory backend via `DEMO_MODE`, keeping identical contracts either way — this is what lets `smoke.py`/CI run without live Atlas access.

No containerization (no Dockerfile/docker-compose) — local dev only, via venv + npm, with strict non-fallback ports for both services.

## Upgrades beyond the original spec

- **Closed memory loop** (`backend/app/memory.py`): deterministic fact extraction from each turn (price sensitivity, defect complaints) with transactional supersession per `(customer_key, fact_type)`. `product_agent` reads active facts back and biases ranking/price ceiling on *later, unrelated* turns — proves memory actually changes behavior, not just a display tab.
- **Weighted product ranking**: `agents.py:_weighted_score` combines relevance (0.55) + rating (0.30) + stock availability (0.15) in one aggregation (`$addFields`/`$sort` in the real Atlas path, equivalent local fallback) — closer to real e-commerce ranking than pure vector similarity.
- **Live coordination feed** (`GET /api/events/stream`, SSE): tails a MongoDB Change Stream on `agent_handoffs`, filtered server-side to the caller's own conversations; falls back to a 1.2s poll loop in `DEMO_MODE`. Frontend consumes it via `fetch` + `ReadableStream` (not `EventSource`, since bearer auth needs a header) in `api.js:streamEvents`, rendered as a live badge + feed in `App.jsx`.
- **LLM-grounded agent responses** (`agents.py:llm_synthesize`): retrieval stays 100% deterministic and ownership-safe (Mongo query built in Python, never by the model), but the final sentence is generated by Anthropic over the *already-fetched* document(s) — covers arbitrary phrasing ("ainda vai demorar muito?") instead of only the handful of templated intents. Falls back to the original f-string template when there's no API key or the model call fails, so `DEMO_MODE`/CI stay deterministic. `product_agent` widens to the full active catalog (local-ranked) when no category/price signal is found, instead of giving up.
- **Self-reinforcing semantic guardrail** (`guardrails.py:check_input` + `_reinforce_denylist`): messages that clear the static denylist go through a cheap LLM classifier (`GUARDRAIL_CLASSIFIER_PERSONA`) that catches novel manipulation attempts (fake authority, social engineering, off-policy demands) the static list doesn't know about yet. A block from the classifier is written back into `guardrail_denylist` (first 8 normalized words as the phrase) — the next similar attempt is caught by the free deterministic path, no LLM call needed. Also supports a third verdict, `DUVIDA` (abstention): instead of a binary block/allow, an uncertain case is logged to `guardrail_candidates` for human review and the turn proceeds — avoids blocking a legitimate customer on a low-confidence call. This moved `check_input`'s call site in `orchestration.py` to *after* the registry/budget load (was before), since the classifier needs an `agent_doc` + `TurnBudget`.
- **Parallel Fan-Out/Synthesis** (`router.py:detect_fanout`, `orchestration.py:_run_fanout`): a compound question naming both an order and a billing signal ("onde está meu pedido e quanto devo?") dispatches `order_agent` + `billing_agent` at the same time via `asyncio.gather` instead of a sequential handoff — genuinely independent work, not chained. Each agent gets a `scope_hint` telling it to answer *only* its own domain and never mention the other topic, since both receive the full compound message. Restricted to the `order_agent`/`billing_agent` pair on purpose — `support_agent`/`product_agent` have a real content dependency (diagnose-then-recommend) and must stay sequential (handoff).
- **JSON Schema validation at the coordination boundary** (`database.py:create_schema_validators`, run from `seed.py`): `agent_handoffs` and `agent_traces` get a `$jsonSchema` validator applied via `collMod`/`create_collection` — MongoDB itself rejects a malformed handoff/trace document, not just the Python layer. No-op in `DEMO_MODE`.
- **Eval harness as a Mongo collection** (`backend/eval.py`, golden dataset in `seed_data.py:EVAL_CASES`): a GoalSuccessRate-style black-box run against the live server (routing correctness, handoff, fan-out, both guardrail types, cross-customer isolation) that writes its pass/fail history to `eval_runs` (`GET /api/eval/runs`, admin-protected; surfaced read-only in the frontend Métricas tab when admin mode is on). Run with `python eval.py [url]`; nonzero exit on any failure, same convention as `tests/smoke.py`.
- **3 new real agents**: `warranty_agent` (coverage by category + purchase date, `warranty_policies`), `loyalty_agent` (points/tier, `loyalty_accounts`, hands off to `product_agent` on redemption intent), `logistics_agent` (carrier/tracking/ETA, `shipments`). All three follow the same deterministic-read + `llm_synthesize` + ownership-safe-filter pattern as the original 4. `order_agent`'s write branch can now hand off to either `billing_agent` or `logistics_agent` depending on what the customer asks after a trade is processed — that handoff check now runs regardless of whether the status *actually changed* this turn (see the routing-stability note below for why). A chain can reach `MAX_HOPS = 4`: e.g. `support_agent` → `product_agent` → `order_agent` → `billing_agent`/`logistics_agent`.
- **Routing stability fixes found via the eval harness/manual multi-agent chain testing** (worth knowing before touching `router.py`): (1) `cheap_route`'s tie-break is purely by seeded `priority` — a generic word like "pedido" was winning ties against more specific intents like "garantia", so `garantia`/`fidelidade`/`logistica` rules are seeded at `priority: 110`, above the generic `status_pedido`/`fatura` rules at 100; (2) Portuguese gender agreement matters for plain substring keyword checks — "parecida" doesn't match a keyword list containing only "parecido", so keyword lists that cover product-alternative intent carry both forms; (3) the LLM orchestrator classification (`orchestration.py`) is only consulted when `deterministic_orchestrator` found *no* keyword at all (`decision.source == "fallback"`) — letting the LLM override an already-confident deterministic match made routing non-reproducible across near-identical messages (temperature-driven).
- **3 more write actions, beyond `order_agent`'s status update** — every agent isn't just read-only anymore: `support_agent` opens a real `support_tickets` document when the customer asks to escalate ("atendente"/"chamado"/"escalar" — *not* on "no KB evidence", since the local-rank fallback in `DEMO_MODE` always returns *some* article regardless of relevance, so that heuristic was almost always true and fired constantly); `loyalty_agent` processes a real point redemption (`$inc` on `loyalty_accounts.points`, restricted to a fixed `REWARD_CATALOG` cost table — never an amount the model invents — plus a `redemptions` audit doc) when the message names a specific reward, separate from its existing handoff-to-`product_agent` path for "resgatar pontos por um produto"; `logistics_agent` can flag a shipment `reschedule_requested: true` (single restricted field, same reconstruct-the-filter pattern as everywhere else) when asked to reschedule delivery.
- **Live "collections in action" panel** (`TimelineEvent.op: "read"|"write"|"vectorSearch"|"hybridSearch"|"changeStream"`, set at every event-creation site in `agents.py`/`orchestration.py`): the Chat page renders a per-turn panel grouping the collections touched this turn with operation badges — the concrete visual answer to "which collections are getting pushed, and how, right now." `orchestration.py:_record_collection_metrics` also increments a cumulative `collection.<name>.<op>` counter into `metrics.py` at every return path (normal turn, cache hit, guardrail block, fan-out), so the session-wide touch count is queryable via `GET /api/metrics`, not just the current turn.
- **Honest cache pre-warming, not fake token usage** (`backend/warmup.py`): before a live demo, run `python warmup.py [url]` to actually call every non-guardrail demo prompt (mirrors `frontend/src/App.jsx:DEMOS_BY_IDENTITY`, same exact text — the cache key is the normalized message) once per identity, for real, against Anthropic. The point isn't to fabricate a fast "first click" — it's that the *first real turn* already happened during warmup, so the customer's live click is a genuine, honestly-labeled `cache_hit: true` replaying the full stored timeline (all agents, all handoffs) rather than a slow cold call. `semantic_cache` TTL was bumped from 15 to 60 minutes for this workflow to survive the walk from warmup to the actual meeting. Never fake `cache_hit`/usage numbers to *look* like the LLM ran when it didn't — that's the one thing this script deliberately does *not* do.
- **All demo prompts trigger 2+ agents or a real write** (`DEMOS_BY_IDENTITY` in `App.jsx`): no more plain single-agent reads as demo buttons — every entry per identity is either a multi-hop chain, a fan-out, a handoff, a real write action, or a guardrail trigger (added to *all four* identities now, not just two). Two routing bugs surfaced writing these and are worth remembering: (1) a keyword belonging to a *later* agent in an intended chain (e.g. "transportadora") can outrank the *first* agent's trigger word (e.g. "troca") in `cheap_route`'s priority tie-break, skipping the earlier hop entirely — phrase compound demo messages to avoid a routing-keyword collision with the wrong hop (e.g. say "entrega" instead of "transportadora" so only `order_agent`'s post-write keyword check catches it, not the initial router); (2) `order_agent`'s billing/logistics handoff used to depend on the status *actually changing* this turn — replaying the same "quero trocar" message after the order was already flipped to `troca_solicitada` (by an earlier turn or eval case) silently dropped the handoff, since eval cases mutate shared seed data across a single run.

## Known gaps (verified against code, not just docs)

- Metrics (`backend/app/metrics.py`) are in-process only, reset on restart — no persistence/aggregation across instances.
- No CI/Docker/deployment config.
- LLM synthesis and the semantic guardrail both cost real Anthropic tokens per turn now (previously only the orchestrator's routing call did) — fine for a demo, would need caching/sampling tuning before high-volume production use.
