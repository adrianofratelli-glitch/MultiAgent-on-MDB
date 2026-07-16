# Arquitetura

## Topologia

```mermaid
flowchart LR
    UI[React / Vite] --> API[FastAPI]
    API --> G[Guardrail de entrada]
    G --> R{Routing rules}
    R -->|óbvio| OA[order_agent]
    R -->|ambíguo| ORC[orchestrator]
    ORC --> OA
    ORC --> PA[product_agent]
    ORC --> SA[support_agent]
    ORC --> BA[billing_agent]
    SA -->|handoff explícito| PA
    OA & PA & SA & BA --> DATA[(multi_agent_poc)]
    ORC --> BRAIN[(ai_brain)]
    DATA --> TRACE[agent_handoffs + agent_traces]
```

## Fluxo de um turno com handoff

```mermaid
sequenceDiagram
    participant C as Cliente
    participant A as API
    participant M as MongoDB Atlas
    participant O as Orchestrator
    participant S as support_agent
    participant P as product_agent

    C->>A: mensagem + JWT
    A->>A: claim sub, rate limit e máscara de PII
    A->>M: guardrail + routing_rules
    A->>O: intenção ambígua
    O-->>A: support_agent
    A->>M: cache(agent=support, area=tenant)
    A->>S: mensagem + contexto bounded
    S->>M: RAG híbrido em kb_articles
    S-->>A: orientação + transferir para product_agent
    A->>M: insert agent_handoffs
    A->>P: contexto do handoff
    P->>M: $vectorSearch em products_catalog
    P-->>A: recomendação
    A->>M: conversa, cache e trace
    A-->>C: resposta consolidada + timeline
```

## Limites de segurança

- O token define `customer_key`; campos de identidade do payload são ignorados.
- Filtros de pedido e fatura são reconstruídos do zero com ownership.
- Somente `order_agent` recebe a ferramenta de escrita, limitada a `$set.status` e estados aprovados.
- O plano `ai_brain` é alterado somente pelos endpoints administrativos.
- Conversas são bounded a 20 mensagens e expiram em uma hora; eventos e auditoria expiram em 30 dias.

## Retrieval

- Catálogo: `autoEmbed` com `voyage-4`, `indexingMethod: flat` e filtros `active`, `category`, `price`.
- Base de suporte: ranking vetorial e BM25 combinados com RRF.
- Memória longa: um documento por fato, com `customer_key + active` no índice vetorial.
- Cache: índice vetorial particionado por `agent + area + customer_key`; o terceiro filtro impede compartilhamento de respostas entre clientes da mesma área. A implementação também aceita hit exato para uma demonstração determinística.
