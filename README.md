# Multi-Agent on MongoDB

I built this PoV to answer a question a few prospects kept asking during multi-agent conversations: "fine, but where does all of this actually *live*?" Most reference architectures answer that with a shopping list — a database for durable state, Redis for session cache, a vector store bolted on the side, maybe a queue to coordinate handoffs. That's four systems to keep in sync before you've written a single line of business logic.

This PoV takes the opposite bet: **MongoDB Atlas is not just where the data lives — it's where the agents coordinate.** Routing rules, agent configuration, conversation memory, handoff history, semantic cache, guardrail decisions, audit traces, vector and hybrid search all live in MongoDB, as documents, queryable the same way you'd query an order or an invoice.

The screenshot below is the moment that usually lands the pitch: a support agent hands off to a product agent, which hands off to the order agent, which hands off to logistics, and the order agent gets called back at the end to confirm the trade actually stuck. Five agents, one customer message, every handoff a document you can query while it's happening.

![Cadeia completa de agentes com retorno controlado](docs/screenshots/03-chain-timeline.png)

## What this actually demonstrates

- **Agents are documents, not deployments.** Each agent's model, persona, tools, and token budget live in `ai_brain.agent_registry`. Disabling an agent, changing its model, or rewriting its persona is a MongoDB update — no redeploy, no restart.
- **Coordination is auditable by design.** Every handoff between agents is written to `agent_handoffs` the moment it happens. A live Change Stream tails that collection and pushes it to the UI in real time.
- **Multi-agent chains, not just single handoffs.** A single customer message can genuinely walk through 4 agents in one turn — diagnose (support) → recommend (product) → process the trade (order, the only agent with write access) → check the invoice impact (billing) — each one strictly scoped to its own part of the question.
- **Parallel fan-out, when it makes sense.** A compound question like "where's my order, and how much do I still owe?" dispatches two independent agents at once instead of chaining them — genuine parallelism where the work doesn't depend on itself.
- **Retrieval is hybrid and native.** Product recommendations use `$vectorSearch` with automatic embedding (`voyage-4`); support articles use BM25 + vector search fused with Reciprocal Rank Fusion — both running as MongoDB aggregation pipelines, not a bolted-on search service.
- **Security is ownership-first.** `customer_key` comes only from the JWT, never from the request body. Every order/invoice/shipment query is rebuilt from scratch server-side. Only one agent can write, and only to one field, from an approved list of values.
- **A guardrail that gets smarter as it runs.** New manipulation attempts caught by an LLM classifier get written back into the fast deterministic denylist — the next similar attempt is blocked instantly, no LLM call needed. Ambiguous cases get flagged for human review instead of blocking a legitimate customer by mistake.
- **A cache cascade with explicit trust boundaries.** Short-term memory is scoped by session + customer + agent; cross-session cache remains customer-scoped; only public catalog/KB answers with no personalized memory, handoff, or write can enter the global cache.
- **An eval harness that lives in the same database.** A golden dataset of test conversations gets replayed against the live server and the pass/fail history is written to `eval_runs` — quality tracking as a MongoDB collection, not a separate dashboard.

![Tela inicial: canal do cliente e roteiro rápido de cenários](docs/screenshots/01-chat-home.png)

## The 8 agents

| Agent | Job | Can write? |
|---|---|---|
| `orchestrator` | Classifies intent, routes, never answers the customer directly | No |
| `order_agent` | Order status, trade/refund requests | Yes — order status only, approved values only |
| `product_agent` | Catalog recommendations via vector search, weighted by relevance + rating + stock | No |
| `support_agent` | Technical troubleshooting via hybrid RAG; opens a real support ticket when it can't resolve | Yes — support tickets |
| `billing_agent` | Invoice lookups | No |
| `warranty_agent` | Coverage checks by product category + purchase date | No |
| `loyalty_agent` | Points balance, tier benefits, real reward redemption | Yes — point deduction, restricted to a fixed reward catalog |
| `logistics_agent` | Carrier, tracking code, delivery ETA; can flag a reschedule request | Yes — reschedule flag only |

Every agent's config — model, persona, tools, budget — is a document in `ai_brain.agent_registry`. You can toggle one off or swap its model mid-demo without touching a line of code.

![Registro de agentes com modelo, escopo e ativação individual](docs/screenshots/04-agents-registry.png)

## Stack

- **Backend:** Python 3.12, FastAPI, PyMongo Async, Anthropic SDK (Claude Haiku for routing/simple agents, Sonnet for reasoning-heavy ones)
- **Frontend:** React + Vite
- **Data platform:** MongoDB Atlas — Search + Vector Search with Automated Embedding (`voyage-4`), Change Streams, JSON Schema validation, TTL indexes

## Running it locally

```bash
cp .env.example .env
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/seed.py
cd backend && python run.py
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5191`. The backend runs on `http://127.0.0.1:8031` by default. Both use strict ports — if one's taken, the process exits instead of silently picking another port.

### Running without a live Atlas cluster

```bash
cd backend
DEMO_MODE=1 AUTH_REQUIRED=1 python run.py
```

Same contracts, same seed data, kept in memory — no Vector Search or Change Streams, but everything else behaves identically. This is what the automated tests and CI run against.

### Before a live demo

Run the warm-up script once, ahead of time, so the customer's first click doesn't eat a cold multi-hop LLM chain:

```bash
cd backend
python warmup.py
```

This calls the real demo prompts against the real model once — genuinely, at real cost — so the semantic cache is populated honestly before anyone's watching. When the customer clicks the same prompt live, `cache_hit: true` is real, not staged.

## Tests

```bash
cd backend
pytest -q                              # unit tests
python tests/smoke.py <url>            # black-box smoke test against a running server
python eval.py <url>                   # golden-dataset eval harness, writes results to eval_runs
```

## The core scenario, in one turn

> "My phone order PED-1001 arrived defective, I want something similar but cheaper, and I want to trade it — does that affect my invoice?"

Watch it walk: **support** diagnoses the defect → hands off to **product**, which recommends a cheaper alternative from the real catalog → hands off to **order**, which processes the trade (the only write in the whole system) → hands off to **billing**, which explains the invoice impact. Four agents, one customer message, every handoff a document in `agent_handoffs` you can query the instant it happens.

## What the customer sees when something goes wrong on purpose

Every demo run includes at least one attempt to break the system — a fake authority claim, a jailbreak prompt, someone asking the assistant to hide a refund from the audit trail. The static denylist and the near-miss checker catch most of it for free; anything novel goes through a cheap LLM classifier that writes the new pattern back into the denylist, so the next attempt never needs a model call at all.

![Painel de guardrails: bloqueios, denylist auto-alimentada e candidatos ambíguos](docs/screenshots/06-guardrails.png)

And because none of this is worth much if you can't prove it happened, the metrics page pulls straight from the same collections everything else writes to — no separate analytics pipeline, no export job.

![Métricas operacionais: cobertura de agentes, handoffs, escritas e buscas nativas](docs/screenshots/05-metrics.png)

## Docs

- [Architecture](docs/architecture.md)
- [ADR-001](docs/adr/ADR-001-arquitetura-multi-agente.md)
