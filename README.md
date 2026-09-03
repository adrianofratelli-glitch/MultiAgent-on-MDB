# Multi-Agent on MongoDB

[![CI](https://github.com/adrianofratelli-glitch/MultiAgent-on-MDB/actions/workflows/ci.yml/badge.svg)](https://github.com/adrianofratelli-glitch/MultiAgent-on-MDB/actions/workflows/ci.yml)

8 customer-service agents that coordinate through MongoDB Atlas — no queue, no Redis, no separate vector store. Routing rules, agent configs, memory, cache, handoffs and guardrail decisions are all documents you can query while the conversation is running.

## The demo in 5 steps

**1. Customer sends one message.**

![Chat home with the demo prompts](docs/screenshots/01-chat-home.png)

**2. It walks through 4 agents in a single turn.** Support diagnoses the defect → product recommends a cheaper item → order processes the trade (the only write) → billing explains the invoice impact. Every hop is a document in `agent_handoffs`, streamed live via Change Streams.

![Agent chain timeline showing four handoffs in one turn](docs/screenshots/03-chain-timeline.png)

**3. Agents are data, not deployments.** Model, persona, tools and token budget live in `agent_registry` — toggle an agent or swap its model mid-demo, no redeploy.

![Agent registry with per-agent model, scope and on/off toggle](docs/screenshots/04-agents-registry.png)

**4. Try to break it.** A jailbreak or fake-authority prompt hits the denylist first; anything new goes to a cheap LLM classifier that writes the pattern back to the denylist, so the next attempt is free.

![Guardrails panel: blocks, self-fed denylist, flagged ambiguous cases](docs/screenshots/06-guardrails.png)

**5. Prove it happened.** Metrics come from the same collections everything else writes to.

![Metrics: agent coverage, handoffs, writes, native searches](docs/screenshots/05-metrics.png)

## The agents

| Agent | Job | Writes? |
|---|---|---|
| `orchestrator` | Classifies intent and routes | No |
| `order_agent` | Order status, trades/refunds | Yes — status only, approved values |
| `product_agent` | Catalog recommendations via `$vectorSearch` | No |
| `support_agent` | Troubleshooting via hybrid RAG, opens tickets | Yes — support tickets |
| `billing_agent` | Invoice lookups | No |
| `warranty_agent` | Coverage by category + purchase date | No |
| `loyalty_agent` | Points, tiers, reward redemption | Yes — point deduction |
| `logistics_agent` | Carrier, tracking, ETA | Yes — reschedule flag |

## Stack

Python 3.12 · FastAPI · React + Vite · Anthropic (Haiku for routing, Sonnet for reasoning) · MongoDB Atlas (Vector Search with auto-embedding `voyage-4`, hybrid RRF, Change Streams, TTL, schema validation).

## Run it

```bash
cp .env.example .env
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/seed.py
cd backend && python run.py     # port 8031
```

```bash
cd frontend && npm install && npm run dev   # port 5191
```

No Atlas cluster? `DEMO_MODE=1 AUTH_REQUIRED=1 python run.py` runs the same contracts in memory (no Vector Search / Change Streams). That's what CI uses.

Before a live demo, `python backend/warmup.py` calls the real prompts once so the cache hits are genuine.

## Tests

```bash
cd backend
pytest -q                       # unit
python tests/smoke.py <url>     # black-box
python eval.py <url>            # golden dataset, results to eval_runs
```

Every pull request runs the backend test suite and Ruff checks, plus a clean
frontend production build and dependency audit. CI uses the deterministic
in-memory data-store implementation and does not require Atlas or Anthropic
credentials.

## Docs

[Architecture](docs/architecture.md) · [ADR-001](docs/adr/ADR-001-arquitetura-multi-agente.md)
