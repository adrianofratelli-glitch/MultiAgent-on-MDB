# Multi-agente no MongoDB

8 agentes de atendimento que se coordenam pelo MongoDB Atlas — sem fila, sem Redis, sem banco vetorial separado. Regras de roteamento, configurações dos agentes, memória, cache, handoffs e decisões de guardrail são todos documentos que você pode consultar enquanto a conversa acontece.

## A demo em 5 passos

**1. O cliente manda uma única mensagem.**

![Tela inicial do chat com os prompts de demonstração](docs/screenshots/01-chat-home.png)

**2. Ela percorre 4 agentes em um só turno.** Suporte diagnostica o defeito → produto recomenda um item mais barato → pedidos processa a troca (a única escrita) → faturamento explica o impacto na fatura. Cada hop é um documento em `agent_handoffs`, transmitido ao vivo por Change Streams.

![Timeline da cadeia de agentes mostrando quatro handoffs em um único turno](docs/screenshots/03-chain-timeline.png)

**3. Agentes são dados, não deploys.** Modelo, persona, ferramentas e orçamento de tokens vivem no `agent_registry` — ligue/desligue um agente ou troque o modelo dele no meio da demo, sem redeploy.

![Registry de agentes com modelo, escopo e chave liga/desliga por agente](docs/screenshots/04-agents-registry.png)

**4. Tente quebrar.** Um jailbreak ou um prompt de falsa autoridade bate primeiro na denylist; o que for novo vai para um classificador LLM barato que escreve o padrão de volta na denylist, então a próxima tentativa sai de graça.

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

Antes de uma demo ao vivo, `python backend/warmup.py` chama os prompts marcados uma vez e reporta quais respostas estáveis foram de fato admitidas pela política de cache `stable_v1`.

## Testes

```bash
cd backend
pytest -q                       # unitários
python tests/smoke.py <url>     # caixa-preta
python eval.py <url>            # golden dataset, resultados em eval_runs
```

## Fronteira de produção

Defina `ENVIRONMENT=production`, `AUTH_REQUIRED=1` e `DEMO_TOKEN_ISSUANCE_ENABLED=0`. A inicialização então falha fechada em caso de segredo de JWT/admin fraco ou padrão, CORS com curinga, autenticação desabilitada ou emissão de token de demo ligada. O `/metrics` é só para admin. O lançador local continua sendo um runtime de PoV; adicione terminação TLS, um IdP corporativo e uma plataforma gerenciada de processos/containers antes de qualquer exposição externa.

## Documentação

[Arquitetura](docs/architecture.md) · [ADR-001](docs/adr/ADR-001-arquitetura-multi-agente.md)
