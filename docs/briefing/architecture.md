# Arquitetura — multiagente-atendimento

> Para "onde está a query X" veja `queries.md`. Para "como o roteamento/checkpoint dos agentes funciona" veja `agent-behavior.md`. Para telas veja `ui-flows.md`. Este arquivo é a visão geral e o "porquê" das decisões estruturais.

## O que é

PoV de atendimento ao cliente multiagente onde o **MongoDB Atlas é tanto o data plane quanto o plano de coordenação**: regras de roteamento, estado dos agentes, handoffs, memória (curto e longo prazo), cache semântico e decisões de guardrail vivem todos em documentos MongoDB, consultáveis como qualquer outro dado operacional — não numa fila/engine de workflow separada.

8 agentes reais registrados em `agent_registry`: `orchestrator`, `order_agent`, `product_agent`, `support_agent`, `billing_agent`, `warranty_agent`, `loyalty_agent`, `logistics_agent`.

**Atenção a uma expectativa importante**: `.claude/rules/scope.md` descreve isto como "8 agentes LangGraph coordenando via Atlas". **Isso não corresponde ao código.** `backend/requirements.txt` não lista o pacote `langgraph`, e não existe `StateGraph`, `add_node`, `add_edge`, `add_conditional_edges` nem `MongoDBSaver` em nenhum lugar do backend (`grep -rn "langgraph\|StateGraph\|MongoDBSaver\|add_node\|add_edge" backend/` não retorna nada). O que existe é uma **orquestração multiagente escrita à mão em Python puro** (`backend/app/orchestration.py`), com uma máquina de handoff sequencial baseada em loop `for hop in range(MAX_HOPS)` e persistência manual em MongoDB — funcionalmente equivalente a um grafo de agentes, mas sem o framework LangGraph por trás. Detalhes completos em `agent-behavior.md`.

## Stack

- **Frontend**: React + Vite (`frontend/src`), porta 5191 (estrita, sem fallback).
- **Backend**: FastAPI (`backend/app/main.py`), porta 8031 (estrita, sem fallback), driver `pymongo` assíncrono (`AsyncMongoClient`).
- **LLM**: Anthropic (`backend/app/llm.py`), usado para (a) classificação de intenção quando a regra determinística empata, (b) síntese da resposta final sobre documentos já buscados no Mongo, (c) classificador de guardrail semântico.
- **Dados/coordenação**: MongoDB Atlas — dois bancos lógicos, `multi_agent_poc` (dados de negócio + estado operacional) e `multiagent_brain` (configuração: `agent_registry`, `routing_rules`, `guardrail_policies`).
- **Busca**: Atlas Vector Search com Automated Embedding (`voyage-4`), Atlas Search (BM25/lexical), `$rankFusion` (MongoDB 8.1+) para híbrido server-side.
- **Observabilidade**: Langfuse self-host (uma trace por turno), Change Streams para live feed de handoffs, métricas in-process (`backend/app/metrics.py`).
- **Modo sem Atlas**: `DEMO_MODE=1` troca `DataStore` para um backend em memória (`backend/app/database.py`) com os mesmos contratos — usado por testes/CI, sem Vector Search/Change Streams reais.

## Componentes principais

| Arquivo | Responsabilidade |
|---|---|
| `backend/app/main.py` | Rotas FastAPI, auth JWT, middleware, SSE de eventos |
| `backend/app/orchestration.py` | `OrchestrationService.run_turn` — o "grafo" de handoff, cache, memória, trace |
| `backend/app/router.py` | Roteamento determinístico por keyword (`cheap_route`), detecção de fan-out, orquestrador fallback |
| `backend/app/agents.py` | Os 7 runners de agente (`RUNNERS`), lógica de negócio de cada um |
| `backend/app/graph.py` | `$graphLookup` sobre `orders` — cadeia de reposição/troca |
| `backend/app/cascade.py` | Cascata de cache semântico (curto prazo → cache global) via `$vectorSearch`/`$unionWith` |
| `backend/app/memory.py` | Extração e supersessão de fatos do cliente (`customer_memory`) |
| `backend/app/retrieval.py` | Pipelines de busca híbrida (`kb_articles`) — vetor, lexical, `$rankFusion` |
| `backend/app/guardrails.py` | 3 camadas de guardrail: denylist estático, denylist vetorial, classificador LLM |
| `backend/app/database.py` | `DataStore` — abstração Atlas real vs. in-memory; índices e validators |
| `backend/app/decisions.py` / `reviews.py` | Trilha de auditoria (`agent_decisions`) e fila de revisão humana (`pending_reviews`) |
| `backend/app/langfuse_client.py` | Uma trace Langfuse por turno inteiro (roteamento, cada hop, handoff, guardrail) |

## Fluxo de dados de um turno (visão de 10.000 pés)

1. **Entrada** — `POST /api/chat`, JWT decodifica `customer_key` (nunca vem do payload).
2. **Guardrail de entrada** — denylist estático → denylist vetorial (Atlas Vector Search) → LLM classificador (só se necessário).
3. **Extração de memória** — fatos simples (`price_sensitive`, `product_complaint`) extraídos da mensagem e gravados com supersessão transacional em `customer_memory`.
4. **Roteamento** — regra determinística por keyword (`cheap_route`) prioritária; LLM só decide quando não há sinal de regra nenhum. Fan-out paralelo (`order_agent` + `billing_agent`) para perguntas compostas genuinamente independentes.
5. **Cascata de cache semântico** — `$vectorSearch` em `short_term_memory` unido (`$unionWith`) com `semantic_cache`; HIT retorna sem chamar LLM nenhum.
6. **Loop de agentes (handoff)** — até `MAX_HOPS = 5` agentes em cadeia, cada um podendo pedir handoff explícito para outro. Cada runner lê o Mongo com filtro de ownership reconstruído, e opcionalmente sintetiza a resposta final via LLM sobre o documento já buscado (nunca o LLM decide o que buscar).
7. **Guardrail de saída** — checa vazamento de segredo/marcador interno.
8. **Persistência** — conversa (`agent_conversations`, delta via `$push`/`$slice`), handoffs (`agent_handoffs`), trace completo (`agent_traces` + Langfuse), métricas cumulativas por collection+operação.

Diagrama de topologia e sequência mais detalhado (Mermaid) já existe em `../architecture.md` (nível de repositório) — este arquivo não duplica os diagramas, foca no "porquê".

## Decisões de arquitetura que valem citar numa call

- **MongoDB como plano de coordenação, não só de dados**: routing rules, registry de agentes, handoffs, cache e decisões são documentos comuns — dá para consultar "por que o agente X decidiu Y" com um `find`, sem instrumentar nada à parte. Ver ADRs em `../adr/`.
- **LLM nunca escolhe o que buscar**: toda leitura no Mongo é construída em Python com filtro de ownership; o LLM só redige a frase final sobre o documento já retornado (`agents.py:llm_synthesize`). Isso mantém a segurança de dados fora do raciocínio do modelo.
- **Roteamento determinístico é a regra, LLM é a exceção**: `cheap_route` (keyword + prioridade seedada) resolve a maioria; o LLM só decide quando não há nenhum sinal de regra, e nunca sobrescreve uma decisão determinística já confiante — sampling variance tornava o roteamento não-reprodutível quando podia.
- **Handoff sequencial vs. fan-out paralelo**: cadeias com dependência real (diagnosticar → recomendar → efetivar) são sequenciais; perguntas genuinamente independentes (status do pedido + valor da fatura) rodam em paralelo via `asyncio.gather`, restrito ao par `order_agent`/`billing_agent` de propósito.
- **Escrita é exceção, não regra**: das 7 agentes só 4 têm qualquer efeito de escrita (`order_agent`, `loyalty_agent`, `logistics_agent`, `support_agent`), e cada write é restrito a um allowlist de valores/campos aprovados — nunca um `$set` arbitrário vindo do LLM.
- **Sem framework de grafo**: a coordenação é um loop Python com controle explícito de visitas, revisão e profundidade máxima — decisão consciente de não trazer uma dependência de orquestração externa para uma PoV cujo ponto de venda é "o MongoDB já é o plano de coordenação".

## Segurança e isolamento

- `customer_key` só existe no JWT; todo filtro de leitura/escrita é reconstruído no backend, nunca aceito do payload (`policies.py`).
- Transações multi-documento (quando o cluster é replica set) amarram escrita de negócio + registro de decisão — `run_in_transaction_with_retry` repete em `TransientTransactionError`.
- `$jsonSchema` validators em `agent_handoffs`, `pending_reviews`, `agent_decisions`, `agent_audit_events`, `agent_traces` — o próprio MongoDB rejeita documento malformado, não só a camada Python.

## Gaps conhecidos (verificados no código, não só na doc)

- Métricas (`metrics.py`) são in-process, resetam a cada restart — sem agregação entre instâncias.
- LLM synthesis e o guardrail semântico custam tokens Anthropic reais por turno — ok para demo, precisaria de cache/sampling antes de volume alto de produção.
- Sem containerização (sem Dockerfile/docker-compose) — dev local via venv + npm.
