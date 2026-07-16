# ADR-001 — Coordenação multi-agente orientada a documentos

- Status: aceito
- Data: 2026-07-15

## Contexto

O atendimento exige agentes especializados, troca explícita de responsabilidade, isolamento por cliente, auditoria e alteração de política sem novo deploy. A PoV precisa demonstrar esses requisitos sem introduzir uma fila ou um motor de workflow apenas para guardar estado de coordenação.

## Decisão

Usar MongoDB Atlas como plano de dados e de coordenação:

- `ai_brain.agent_registry` define o time de agentes, modelos, ferramentas e budgets;
- `ai_brain.routing_rules` mantém regras determinísticas de primeiro nível;
- `agent_conversations` guarda somente o contexto curto, bounded e com TTL;
- `agent_handoffs` e `agent_traces` são eventos independentes e consultáveis;
- dados operacionais, memória longa, cache e guardrails mantêm filtros de tenant nos próprios documentos e índices.

O orquestrador não responde ao cliente. Casos inequívocos não pagam uma chamada de modelo; ambiguidades passam pelo orquestrador. Um agente pode transferir uma vez e o turno percorre no máximo dois agentes.

## Por que multi-agente aqui

Os domínios têm permissões, fontes, modelos e budgets realmente diferentes. O `order_agent` pode alterar apenas estados aprovados; cobrança é somente leitura; produto e suporte usam estratégias de retrieval distintas. Essa separação reduz o blast radius e deixa responsabilidade e custo auditáveis.

## Por que o registry é um documento

A configuração muda com mais frequência que o código e precisa ser inspecionada na demonstração. Um documento permite ativação, troca de modelo, persona e budget de forma atômica, auditada e sem redeploy. A aplicação continua aplicando uma allowlist de ferramentas: documento configura política, mas não ganha capacidade arbitrária.

## Consequências

- A colaboração pode ser consultada por `conversation_id` e agregada por agente.
- TTL cuida do ciclo de vida operacional sem jobs externos.
- O fallback local de RRF funciona em versões anteriores; Atlas 8.0+ pode mover a fusão para `$rankFusion`.
- Em escala maior, revisitaremos particionamento de traces, arquivamento e Change Streams para consumidores assíncronos. Uma fila só será adicionada quando existir trabalho assíncrono real, não para representar handoff síncrono.

