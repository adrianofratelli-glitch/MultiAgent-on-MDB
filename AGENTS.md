# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

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
```

Before a live demo, pre-warm the semantic cache so the customer's first click isn't a cold multi-hop LLM chain:
```bash
python backend/warmup.py http://127.0.0.1:8031
```
This calls every non-guardrail demo prompt (mirrors `frontend/src/App.jsx:DEMOS_BY_IDENTITY` verbatim — cache key is the normalized message) once per identity, for real, against Anthropic. It's honest pre-warming, not fabricated usage: the first real turn already happened during warmup, so the live click is a genuine `cache_hit: true` replaying the full stored timeline. `semantic_cache` TTL is 60 minutes to survive the walk from warmup to the meeting.

Backend lint (ruff configured in `pyproject.toml`, no wrapper script):
```bash
cd backend && ruff check .
```

Frontend build: `cd frontend && npm run build` (no frontend lint/test script defined).

## Architecture

**Flow:** frontend (React/Vite, `frontend/src/api.js`) → REST → backend (FastAPI, `backend/app/main.py`), JWT bearer auth via `/api/auth/token`, admin actions (toggling an agent, viewing eval history) gated by `X-Admin-Key` header.

**Orchestration** (`backend/app/orchestration.py`, `router.py`, `agents.py`): each turn passes an input guardrail, then routes via a cheap deterministic rule (`ai_brain.routing_rules`) or, only if no rule matched at all, the orchestrator LLM classifies intent. **The LLM never overrides an already-confident deterministic decision** — sampling variance made routing non-reproducible across near-identical messages when it could. `cheap_route`'s tie-break is by seeded `priority`; more specific intents (`garantia`/`fidelidade`/`logistica`) are seeded above generic ones (`status_pedido`/`fatura`) so a compound message routes to the right first agent. A turn can chain up to `MAX_HOPS = 4` agents (e.g. `support_agent` diagnoses → `product_agent` recommends → `order_agent` processes the trade, its only restricted write → `billing_agent`/`logistics_agent` confirms the follow-up); every handoff persists to `agent_handoffs`/`agent_traces` and drives the UI Timeline/Inspector. A genuinely independent compound question (order status + invoice) instead fans out `order_agent` + `billing_agent` in parallel via `asyncio.gather` (`router.py:detect_fanout`, `orchestration.py:_run_fanout`) rather than chaining — restricted to that pair on purpose, since `support_agent`/`product_agent` have a real diagnose-then-recommend dependency. Each agent's grounding instructions (`agents.py:GROUNDING_RULES`) tell it to silently ignore parts of a compound message outside its own domain rather than commenting on them — without this, agents mid-chain hallucinate policy for domains they don't own.

**Agent config is data, not code**: `ai_brain.agent_registry` holds each agent's model, persona, tools, and budget — editable at runtime with no redeploy (`AgentUpdate` model in `backend/app/models.py`).

**LLM-grounded responses** (`agents.py:llm_synthesize`): retrieval stays 100% deterministic and ownership-safe (Mongo query built in Python, never by the model), but the final sentence is generated by Anthropic over the *already-fetched* document(s) — covers arbitrary phrasing instead of only templated intents. Falls back to an f-string template when there's no API key or the call fails, so `DEMO_MODE`/CI stay deterministic.

**Write actions** (beyond `order_agent`'s status update, restricted to an approved-values allowlist): `support_agent` opens a real `support_tickets` document on explicit escalation ("atendente"/"chamado"/"escalar" — not on "no KB evidence," since the `DEMO_MODE` local-rank fallback always returns *some* article regardless of relevance); `loyalty_agent` processes a real point redemption (`$inc` on `loyalty_accounts.points`, restricted to a fixed `REWARD_CATALOG` cost table, plus a `redemptions` audit doc) or hands off to `product_agent` for "redeem points for a product"; `logistics_agent` can flag `shipments.reschedule_requested: true` (single restricted field). `order_agent`'s post-write handoff to `billing_agent`/`logistics_agent` runs regardless of whether the status *actually changed* this turn — depending on an in-turn state change meant replaying "quero trocar" after an earlier turn/eval case had already flipped the order silently dropped the handoff.

**Security model** (`backend/app/security.py`, `policies.py`, `guardrails.py`): `customer_key` comes only from the JWT, never the request payload — every query is filtered by it, filters reconstructed server-side. Conversations are bounded (20 messages / 24h TTL, resumable via `GET /api/conversations/latest`, which also replays the last turn's timeline so a resumed session doesn't look like nothing happened); audit events expire after 30 days. `budget.py` enforces per-turn token budgets (`BudgetExceeded`); `rate_limit.py` is a sliding-window limiter.

**Self-reinforcing guardrail** (`guardrails.py:check_input`): static denylist + near-miss check first (free). If nothing matched *and* the message didn't already hit a confident routing rule (`skip_semantic` — routing-safe messages skip the extra LLM call entirely, cutting real Anthropic cost), a cheap LLM classifier catches novel manipulation attempts and writes a block back into `guardrail_denylist` so the next similar attempt is free. A third verdict, `DUVIDA` (abstention), logs an uncertain case to `guardrail_candidates` for human review instead of blocking a possibly-legitimate customer.

**Retrieval** (`backend/app/retrieval.py`): Atlas Vector Search with Automated Embedding (`voyage-4`) over the product catalog, ranked by relevance (0.55) + rating (0.30) + stock (0.15) in one aggregation; hybrid BM25+vector RRF over `kb_articles`.

**Data store abstraction** (`backend/app/database.py`): `DataStore` toggles between real Atlas and an in-memory backend via `DEMO_MODE`, same contracts either way — what lets `smoke.py`/`eval.py`/CI run without live Atlas access. `agent_handoffs`/`agent_traces` get a `$jsonSchema` validator (`create_schema_validators`, no-op in `DEMO_MODE`) so MongoDB itself rejects a malformed document, not just the Python layer.

**Live observability**: `GET /api/events/stream` (SSE) tails a Change Stream on `agent_handoffs`, filtered to the caller's own conversations (poll fallback in `DEMO_MODE`); the frontend shows only the latest handoff, reconnecting automatically on drop (`api.js:streamEvents`). Every `TimelineEvent` also carries an `op` (`read`/`write`/`vectorSearch`/`hybridSearch`/`changeStream`), rendered as a per-turn "collections in action" panel and rolled into cumulative `collection.<name>.<op>` counters in `metrics.py` (`GET /api/metrics`).

**Frontend demo prompts** (`DEMOS_BY_IDENTITY` in `App.jsx`): every entry per identity triggers 2+ agents, a real write, or a guardrail — no plain single-agent reads. Two routing gotchas surfaced building these: a keyword belonging to a *later* agent in an intended chain (e.g. "transportadora") can outrank an *earlier* agent's trigger word (e.g. "troca") in `cheap_route`'s priority tie-break and skip the hop — phrase compound messages to avoid the collision (e.g. "entrega" instead of "transportadora"); Portuguese gender agreement matters for substring keyword checks ("parecida" needs its own entry, not just "parecido").

No containerization (no Dockerfile/docker-compose) — local dev only, via venv + npm, with strict non-fallback ports for both services.

## Known gaps (verified against code, not just docs)

- Metrics (`backend/app/metrics.py`) are in-process only, reset on restart — no persistence/aggregation across instances.
- No CI/Docker/deployment config.
- LLM synthesis and the semantic guardrail both cost real Anthropic tokens per turn — fine for a demo, would need caching/sampling tuning before high-volume production use.
