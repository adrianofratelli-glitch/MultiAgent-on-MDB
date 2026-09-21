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

**4. Tente quebrar — inclusive com pergunta aleatória.** Um jailbreak ou um prompt de falsa autoridade bate primeiro na denylist; o que for novo vai para um classificador LLM barato que escreve o padrão de volta na denylist, então a próxima tentativa sai de graça. O corte de bloqueio automático é **medido**, não chutado: o vetor não separa fraude de reembolso legítimo ("não recebi meu pedido, quero o dinheiro de volta" pontua 0,8664 contra uma frase de fraude), então acima do maior score legítimo medido ele bloqueia sozinho e na faixa ambígua quem decide é o classificador — cliente nunca é barrado por vizinhança vetorial. E "qual é a temperatura hoje?" não é ataque: recebe orientação educada com **0 tokens**, sem agente e sem cache, marcada como `🧭 Guardrail de escopo`. Quem decide o que é da loja não é uma lista de palavras: é uma busca vetorial (`scope_probes`) que entende inglês, gíria e erro de digitação, e só chama o LLM na faixa ambígua. Medido em **229 situações geradas por LLM** (com holdout): acerto **87,3% → 97,5%** no holdout, 0% de cliente legítimo bloqueado.

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
pytest -q                       # unitários (380, sem rede)
python tests/smoke.py <url>     # caixa-preta
python eval.py <url>            # golden dataset, resultados em eval_runs

# modo LIVE — Atlas e LLM REAIS (custa tokens; identidade descartável, limpa o que gravou)
LIVE=1 pytest tests/test_live.py -q            # ~2 min — contratos essenciais
LIVE=1 pytest tests/test_live_random.py -q     # ~4 min — perguntas aleatórias e fora de escopo
LIVE=1 pytest tests/test_live_scenarios.py -q  # ~10 min — jornada completa dos 4 clientes
python eval_situations.py                      # ~5 min — 229 situações geradas por LLM contra o agente real (dev vs holdout)
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

## Observability opcional: Langfuse

Com `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` no `.env` (`backend/app/langfuse_client.py`), cada turno vira UMA trace cobrindo a timeline inteira — roteamento, decisão de cache e cada hop de agente com seu handoff, não só um número de cache hit-rate isolado. Cada agente que respondeu vira uma generation; cache/handoff/memória/guardrail viram spans. Fail-open: sem as chaves, ou com o Langfuse fora do ar, vira no-op (`auth_check()` roda uma vez por processo, então um Langfuse indisponível nunca expõe um link que dê 404 no meio de uma demo). Badge "Ver trace no Langfuse" e card "Economia MongoDB" (cascata semântica + prompt cache) aparecem no cabeçalho do turno, na própria UI.

## Fronteira de produção

Defina `ENVIRONMENT=production`, `AUTH_REQUIRED=1` e `DEMO_TOKEN_ISSUANCE_ENABLED=0`. A inicialização então falha fechada em caso de segredo de JWT/admin fraco ou padrão, CORS com curinga, autenticação desabilitada ou emissão de token de demo ligada. O `/metrics` é só para admin. O lançador local continua sendo um runtime de PoV; adicione terminação TLS, um IdP corporativo e uma plataforma gerenciada de processos/containers antes de qualquer exposição externa.

## Documentação

[Arquitetura](docs/architecture.md) · [ADR-001 — coordenação orientada a documentos](docs/adr/ADR-001-arquitetura-multi-agente.md) · [ADR-002 — memória por LLM e turno pessoal fora do cache](docs/adr/ADR-002-memoria-llm-e-turno-pessoal.md) · [ADR-003 — guardrail em duas faixas e fora de escopo](docs/adr/ADR-003-guardrail-em-duas-faixas.md) · [ADR-004 — escopo por embedding e medição por situações](docs/adr/ADR-004-escopo-por-embedding-e-medicao-por-situacoes.md)
