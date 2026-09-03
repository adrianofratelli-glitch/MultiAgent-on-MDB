# Multi-Agent on MongoDB — arquitetura e princípios

> Primeira das três partes do briefing desta PoV. Os oito agentes, o roteamento, a coordenação, o guardrail e a segurança. Coleções, índices, cache e memória em `02-mongodb.md`; tela e roteiro em `03-interface-fluxos.md`.

---

## O que eu quero construir

Uma PoV de atendimento ao cliente com **oito agentes coordenados**, onde o MongoDB Atlas é ao mesmo tempo o data plane e o coordination plane. Regra de roteamento, estado de agente, handoff, memória, cache, decisão de guardrail, roteiro de demo, histórico de avaliação — tudo isso é documento no Mongo e sai numa query comum.

O que eu quero provar é uma coisa só: **não precisa de fila, workflow engine e vector DB separados pra orquestrar agente.** Um cluster Atlas cobre os três papéis. E o efeito colateral disso, que pra mim é o melhor argumento, é que toda decisão da orquestração fica inspecionável.

Antes de codar, escreve um ADR justificando MongoDB no lugar de fila + engine de workflow. Ele mora em `docs/adr/ADR-001-arquitetura-multi-agente.md`, e a arquitetura completa em `docs/architecture.md`.

## Os oito agentes

Todos registrados em `multiagent_brain.agent_registry`:

| Agente | Domínio | Escrita permitida |
| --- | --- | --- |
| `orchestrator` | classifica intenção quando nenhuma regra determinística casa | — |
| `order_agent` | status, troca e reembolso de pedido | `status` do pedido, restrito a allowlist de valores |
| `product_agent` | catálogo e recomendação | — |
| `support_agent` | diagnóstico e base de conhecimento | abre `support_tickets` só em escalação explícita |
| `billing_agent` | faturas e cobrança | — |
| `warranty_agent` | garantia por categoria e data de compra | — |
| `loyalty_agent` | pontos, tier e resgates | `$inc` em `loyalty_accounts.points` + doc de auditoria em `redemptions` |
| `logistics_agent` | rastreio, previsão e reagendamento | `shipments.reschedule_requested`, campo único |

**São oito. Se o registry diz N agentes, N respondem.** Numa versão anterior o registry foi inflado com uns 120 documentos inertes só pra poder dizer "100+ agentes" — eu revertei isso de propósito. Não reintroduz documento no-op pra engordar contagem, porque a primeira coisa que uma banca técnica faz é pedir pra ver um deles funcionando, e aí acabou a conversa.

O `orchestrator` não tem runner próprio — ele roteia, não fala com o cliente. Os sete especialistas ficam num dicionário `RUNNERS` em `agents.py`, e a chave do dicionário é a mesma `agent_key` do registry.

**Configuração de agente é dado, não código.** Cada documento carrega `agent_key`, `label`, `model`, `fallback_model`, `persona`, `allowed_tools`, `max_turn_tokens`, `max_output_tokens` e `active`. Trocar o modelo do `support_agent` de Sonnet pra Haiku tem que ser um `update_one`, sem redeploy — eu faço isso ao vivo na demo, pela aba Agentes.

Um detalhe que me custou caro: **`max_turn_tokens` e `max_output_tokens` são campos diferentes.** O primeiro é o budget do turno inteiro daquele agente (persona + grounding + contexto recuperado + memória + saída). O segundo é só o teto de saída que vai pra API. Eu tinha os dois no mesmo campo, aí a cascata de memória de longo prazo começou a injetar uns 600 tokens de contexto e o budget estourava antes da primeira resposta sair.

## Roteamento: determinístico primeiro, LLM só como último recurso

Essa regra aqui não se negocia:

> **O LLM nunca sobrepõe uma decisão determinística que já veio confiante.**

Eu já deixei ele sobrepor, e a variância de sampling tornou o roteamento não-reprodutível: dois clientes escrevendo praticamente a mesma frase caíam em agentes diferentes. Isso é inaceitável numa demo e pior ainda em produção.

A cadeia de decisão, em ordem (`router.py`):

1. **`cheap_route(message, rules)`** — casa `multiagent_brain.routing_rules` por palavra-chave, com fronteira de palavra (`(?<!\w)…(?!\w)`, não substring solta) e texto normalizado sem acento. Pontua por `(quantas keywords casaram, priority)`. **Se o melhor empate apontar pra agentes diferentes, devolve `None`** e deixa o orquestrador resolver — empate silencioso é pior que uma classificação a mais.
2. **`deterministic_orchestrator(message)`** — segunda passada por palavra-chave, Python puro: defeito/suporte → `support_agent` (0.82), produto/categoria/"mais barato" → `product_agent` (0.78), fatura/cobrança/boleto → `billing_agent` (0.82), e o fallback puro → `order_agent` com confiança **0.55**.
3. **Classificador LLM** — só entra quando o passo 2 devolveu `source == "fallback"`, ou seja, quando não apareceu palavra-chave nenhuma. O `orchestrator` recebe as chaves permitidas e responde **uma linha**, só a chave. Parseia a primeira linha; se não bater exato, procura a chave dentro do texto; se nada bater, mantém o determinístico.

As regras seedadas, com a prioridade que importa:

| intent | keywords | agente | priority |
| --- | --- | --- | --- |
| `defeito` | defeito, quebrado | `support_agent` | 120 |
| `garantia` | garantia, garantido | `warranty_agent` | 110 |
| `fidelidade` | pontos, fidelidade, resgatar, milhas | `loyalty_agent` | 110 |
| `logistica` | rastreio, transportadora, rastreamento, reagendar… | `logistics_agent` | 110 |
| `status_pedido` | pedido, onde está, PED- | `order_agent` | 100 |
| `fatura` | fatura, FAT- | `billing_agent` | 100 |
| `troca` / `reembolso` / `cobranca` / `vencimento` | … | conforme | 90 |
| `recomendacao` / `produto_similar` / `suporte` | … | conforme | 80 |

As intenções específicas ficam **acima** das genéricas de propósito. Numa mensagem composta tipo "o carregador do PED-3002 está na garantia? quero um parecido mais barato", quem tem que atender primeiro é o `warranty_agent`, não o `order_agent` que casou "pedido".

Duas coisas que eu só descobri montando os prompts de demo, e que você vai esbarrar também:

- Palavra-chave de um agente **mais pra frente** na cadeia pode ganhar do gatilho do agente **anterior** no desempate por prioridade, e aí ele pula o hop. "transportadora" (110) ganhando de "troca" (90), por exemplo. Eu frasei as mensagens compostas fugindo dessa colisão — usa "entrega" no lugar de "transportadora" quando quiser que a troca venha antes.
- Gênero em português importa em checagem de substring. "parecida" precisa da entrada dela; não basta ter "parecido". Mesma coisa com "mais barata".

## Cadeia, retorno controlado e fan-out

Um turno pode encadear até **`MAX_HOPS = 5`** agentes quando existe dependência de verdade. A cadeia mais longa da demo é essa: `support_agent` diagnostica → `product_agent` recomenda → `order_agent` processa a troca → `logistics_agent` consulta a entrega → `order_agent` confirma o registro final.

Repara no quinto hop, porque é aí que mora o problema: **é uma revisita.** Sem tratar isso, o loop de handoff vira grafo cíclico e a coisa não termina nunca. Como eu resolvi:

- `ALLOWED_REVISITS = {("logistics_agent", "order_agent")}` — é o único retorno permitido, porque é o único que representa dependência de negócio real ("confirme que a troca ficou registrada depois de ver a entrega").
- `MAX_VISITS_PER_AGENT = 2`, contando visita por turno. Isso mantém o grafo finito **mesmo se alguém editar o registry em runtime e criar um ciclo sem querer** — e como configuração é dado, isso vai acontecer uma hora.
- Handoff pro próprio agente, ou revisita fora da allowlist, não estoura exceção. Encerra a cadeia com uma frase honesta ("o agente de destino já atuou neste turno; mantive a orientação sem criar um handoff circular").
- Na Timeline, retorno permitido aparece como **"Retorno controlado"**, não como "Handoff explícito". Essa diferença precisa estar visível na tela, porque é ela que separa "o sistema voltou de propósito" de "o sistema entrou em loop".

Quando as perguntas são genuinamente independentes ("qual o status do meu pedido e da minha fatura?"), faz **fan-out paralelo** com `asyncio.gather` em vez de encadear (`router.py:detect_fanout`, `orchestration.py:_run_fanout`).

Restringe o fan-out ao par `order_agent` + `billing_agent` (`FANOUT_ELIGIBLE`). E aborta o fan-out se **qualquer agente fora desse par** também casar na mensagem, porque `support_agent` e `product_agent` têm dependência real — tem que diagnosticar antes de recomendar. Paralelizar esses dois te dá recomendação sem diagnóstico, que é pior que resposta lenta.

No fan-out, cada agente recebe uma instrução de escopo bem agressiva ("sua resposta deve conter SOMENTE o assunto pedido/entrega; não escreva nenhuma frase sobre o outro assunto, nem pra dizer que não tem acesso"). Sem esse nível de insistência os dois respondem com um parágrafo de desculpa sobre o tema do outro, e a resposta final sai com quatro parágrafos onde devia ter dois. A chave de cache desse turno é `"order_agent+billing_agent"`, o `route_source` é `fanout` e o `active_agent` também.

Todo handoff vira documento em `agent_handoffs` e o turno inteiro vira documento em `agent_traces`. É daí que sai a Timeline da UI e o `/api/handoffs`.

Dá pra cada agente instrução de grounding (`agents.py:GROUNDING_RULES`) mandando **ignorar em silêncio** as partes da mensagem que estão fora do domínio dele. Sem isso, agente no meio da cadeia começa a comentar política de área que não é dele — desconto, ajuste de fatura — ou seja, alucina com confiança. A regra também proíbe, com todas as letras, dizer "não tenho acesso a isso": outro agente da cadeia já está cuidando daquilo.

**Contexto entre turnos vive na conversa, não no prompt.** `agent_conversations` guarda `active_order_id` e `active_invoice_id`, que é o último `PED-`/`FAT-` que algum agente de fato tocou. É isso que faz o `logistics_agent` saber de qual pedido o cliente está falando no terceiro hop sem a mensagem repetir o número. Detecta isso **por chave no `result` do evento** (`order_id`, `invoice_id`), nunca por nome de collection — o `warranty_agent` grava evento sobre `warranty_policies` e o `logistics_agent` sobre `shipments`, e os dois carregam `order_id`.

## Resiliência: o beco sem saída é um bug de produto

Regra que vale pra todo caminho de falha: **o turno nunca termina sem próximo passo.**

E a regra que impede isso de virar conversa fiada: **toda orientação é derivada de query.** Nada de "você quer perguntar sobre um pedido?" no vazio — sempre "quer acompanhar o PED-1001 (Fone Pulse X, enviado)?", com o id lido de `orders` naquele instante. Sugestão genérica é clicada, falha, e devolve o beco sem saída um turno depois, agora com a credibilidade gasta.

Isso vive em `app/guidance.py`, e tem quatro entradas:

| Situação | O que acontece |
|---|---|
| **Fora de escopo** (assunto aleatório, teste, texto sem sentido) | o orquestrador assume o turno, diz o que o atendimento cobre e lista o que existe para aquela identidade. Determinístico, sem custo de LLM |
| **Saudação / agradecimento / "você é um robô?"** | resposta própria pra cada um. Um "oi" respondido com "isso está fora do meu escopo" é o pior primeiro contato possível — e é o que qualquer pessoa testando digita primeiro |
| **Busca sem resultado** (`PED-9999`) | lista os pedidos reais do cliente, com número e status, em vez de "confira o número do pedido" |
| **Guardrail bloqueou** | o bloqueio continua intacto — o texto não amolece nem negocia — mas leva junto o caminho de volta. Quem testou o limite de propósito vê o limite funcionando **e** o que dá pra fazer |

Duas decisões de roteamento sustentam isso:

- **`has_domain_signal()`** — um vocabulário amplo do domínio responde a UMA pergunta: "essa mensagem tem qualquer vínculo com esta loja?". Não tem nenhum → orientação, sem gastar uma chamada de classificação. Deliberadamente generoso: falso-negativo aqui manda alguém pra orientação, que ainda é uma boa resposta; falso-positivo devolve o palpite genérico que a gente quer matar.
- **O classificador LLM pode responder `nenhum`.** Sem essa saída ele escolhe um agente por eliminação, e o cliente recebe uma resposta sobre pedido pra uma pergunta que não era sobre pedido. Antes disso, mensagem sem sentido caía no `order_agent` com confiança 0.55 — o pior desfecho possível numa demo, porque parece que o roteador chutou.

Cada resposta também devolve `suggestions[]` — os mesmos próximos passos, estruturados, que a UI renderiza como chips clicáveis. O tema que o turno acabou de cobrir é **excluído**: sugerir de volta o que a pessoa acabou de perguntar é pior que não sugerir nada.

E os agentes ganharam saída digna nos próprios becos: `loyalty_agent` pedindo algo fora da tabela de recompensas devolve a tabela real com o custo e quanto falta; saldo insuficiente diz quanto falta e o que já dá; `product_agent` sem resultado na categoria diz o preço da opção ativa mais barata dela; `support_agent` sem artigo relevante pede os três dados que ele precisa pra diagnosticar, ou abre chamado.

### O que quebrou quando eu ataquei de propósito

Cinco correções que só apareceram atacando a PoV, não construindo. Estão aqui porque cada uma é uma armadilha que volta se alguém "simplificar" o código depois:

| Sintoma | Causa | Correção |
|---|---|---|
| Digitar só `PED-1001` caía no fallback | A keyword `PED-` do seed **nunca casava**: o lookahead `(?!\w)` exige não-palavra à direita, e depois do hífen vem dígito. Era letra morta desde sempre — as mensagens de demo escondiam isso por trazerem "pedido" junto | Fronteira à direita só quando a keyword termina em caractere de palavra. `troca` continua não casando `trocador` |
| "o pedido PED-1001 **do bruno**" → *"pertence a outro cliente"* | A query trouxe o pedido certo da própria cliente, e o **modelo** inventou a narrativa a partir do nome citado. O raio-x na tela mostrava o documento e o texto dizia o oposto | `GROUNDING_RULES` + o `extra` do `order_agent`: todo documento que chega é do cliente autenticado; nome de terceiro é ruído |
| Repetir a mesma pergunta numa conversa nova dava MISS | Texto idêntico pontua **0.8101–0.9213** neste índice (frase curta fica na faixa baixa) e o corte do cache era 0.83 | Corte para a banda medida + **match exato por `question_norm`** quando o vetorial não acha: idêntico sempre é HIT |
| Cliente cola o próprio CPF → *"você violou a política"* | O loop auto-reforçante aprendeu a frase mascarada de um teste e passou a bloquear qualquer cliente ingênuo | O reforço ignora frase que é só PII mascarada, e o bloqueio por PII do próprio cliente orienta em vez de acusar |
| Turno servido do cache não aparecia em `short_term_memory` | HIT retornava antes de gravar. A memória da conversa ficava com buracos e uma reformulação seguinte não achava nada na sessão | HIT também grava no curto prazo: essa collection registra a **conversa**, não o custo |

E uma sexta, que eu mesmo causei ao corrigir as outras: acrescentar duas frases ao `GROUNDING_RULES` — que é **compartilhado por todos os agentes** — derrubou três cenários com **HTTP 429**, budget do `warranty_agent` excedido. Ele rodava a menos de 45 tokens do teto. Budget apertado quebra quando o prompt cresce, e o prompt sempre cresce: os `max_turn_tokens` agora têm ~35% de folga, e o texto compartilhado ficou curto de propósito.

O padrão que liga as cinco primeiras: **nenhuma apareceu no caminho feliz.** Rodar o roteiro de demo do começo ao fim passava em todas. Elas só saíram quando alguém digitou o que não estava no script.

## Guardrail auto-reforçante

Três camadas, da mais barata pra mais cara, em `guardrails.py:check_input`:

1. **Denylist estática por substring.** Frase exata, custo zero. São os documentos com `layer: "lexical"`.
2. **Denylist semântica via Atlas Vector Search** — a camada que bloqueia **paráfrase**, de forma determinística e **sem chamar LLM**. Ela continua valendo quando o `skip_semantic` desliga o classificador, e também quando a mensagem já casou uma regra de roteamento. Índice e pré-filtro em `02-mongodb.md`.
3. **Classificador LLM**, só pros fraseados que nenhuma das duas listas conhece ainda. Quando ele bloqueia, **grava o bloqueio de volta em** `guardrail_denylist` — aí a próxima tentativa parecida sai de graça, pela camada 2.

Eu quero um terceiro veredito além de bloqueado/liberado: **`DUVIDA`**. Caso ambíguo não bloqueia, vai pra `guardrail_candidates` pra revisão humana, com `source: "semantic_llm_uncertain"`. Bloquear cliente legítimo é pior que deixar passar um caso limítrofe pra alguém olhar depois. A persona do classificador diz isso explicitamente: "na dúvida real, prefira DUVIDA a arriscar bloquear cliente de verdade".

Tem também um **near-miss vetorial**: score entre `vector_threshold - 0.04` e o threshold não bloqueia, mas entra em `guardrail_candidates` com `source: "denylist_vetorial"`. Promoção de candidato pra denylist **nunca é automática** — passa por `POST /api/admin/guardrails/candidates/{id}/approve`. Se fosse automática, bastava alguém repetir uma frase quase-limítrofe pra envenenar a lista inteira.

O `overlap_score` (Jaccard) serve só de fallback pro `DEMO_MODE`/CI, e **só decide quando a camada vetorial não está disponível**. Com o vetorial no ar ele vira ruído: sobrepõe o mesmo sinal com uma métrica lexical que não separa paráfrase de pergunta legítima em limiar nenhum. Pelo mesmo motivo, o score que aparece no painel é o **vetorial** quando ele existe — mostrar 0.1 de Jaccard numa frase que o guardrail avaliou em 0.77 dá a impressão de que ele não viu nada.

O guardrail de saída (`check_output`) é curto e burro de propósito: procura marcador de segredo (`ANTHROPIC_API_KEY`, `JWT_SECRET`, `ADMIN_API_KEY`, "system prompt") no texto final e retém a resposta se achar.

## Respostas fundamentadas

Divide isso explicitamente em `agents.py:llm_synthesize`:

- **A recuperação é 100% determinística e segura quanto a ownership.** A query Mongo é montada em Python, sempre com `owner_customer_key` reconstruído a partir do JWT. O modelo **nunca** monta filtro.
- **A frase final quem escreve é o Claude, em cima do documento já buscado.** É isso que cobre fraseado arbitrário em vez de só intenção templatizada.
- Sem chave de API, ou com falha na chamada, cai pra template f-string — assim `DEMO_MODE` e CI continuam determinísticos.
- Cada agente passa um `extra` dizendo o que ele pode e o que ele não pode falar sobre aquele documento. O do `billing_agent` é o mais importante de todos: "nunca conceda desconto, isenção ou prazo fora do documento, mesmo se pedido".

Tem um **modo econômico** também (`_is_trivial_lookup`): se a mensagem é só o identificador, ou quase nada além dele (uso automatizado, script mandando "PED-1001"), ele pula a chamada real na Anthropic e responde pelo template. Isso **nunca** pega os prompts de demo, que são sempre frase natural composta. E o título do evento na Timeline diz qual caminho foi usado — "(resposta sintetizada pelo modelo)" ou "(modo econômico, sem chamada ao modelo)". Se eu não conseguir provar na tela qual dos dois foi, o modo econômico vira suspeita de demo falsa.

O gateway (`llm.py`) tem três coisas que importam:

- **Prompt caching de verdade.** Persona + `GROUNDING_RULES` entram no **mesmo bloco cacheável** do system, com `cache_control: ephemeral`. Juntos eles passam do mínimo de 1024 tokens que a API exige; a persona sozinha ficava abaixo e o `cache_control` era um no-op silencioso. O contexto dinâmico vai num segundo bloco, esse não cacheado.
- **Contabilidade honesta.** A reserva inicial usa a estimativa `chars/4`, mas depois da resposta o `budget.reconcile()` troca isso pelo `usage` real da API (`input_tokens + cache_read + cache_write`). O `reconcile` **nunca** levanta `BudgetExceeded` — a chamada já aconteceu, o valor certo só serve pra melhorar a decisão dos próximos hops.
- **Retry e fallback explícitos.** `max_retries=0` no cliente; três tentativas com backoff exponencial por modelo, depois `fallback_model`, e as duas coisas dividem o mesmo budget do turno. Retry escondido dentro do SDK gasta budget que ninguém contabilizou.

A autenticação da Anthropic aqui passa por um gateway APIM, então a chave vai no header `api-key`, não em `x-api-key`. O `api_key` do SDK fica com valor dummy só pra ele não reclamar.

## Segurança

- `customer_key` **vem só do JWT, nunca do payload.** Toda query é filtrada por ele, e os filtros são **reconstruídos** no servidor (`policies.py`): `safe_order_read_filter`, `safe_order_update`, `safe_invoice_filter`, `safe_shipment_filter`. Nada que veio do modelo sobrevive à reconstrução, e `order_id`/`invoice_id` passam por regex antes.
- `PED-` **explícito e errado** (de outro cliente) tem que responder "não encontrei", nunca resolver outro pedido em silêncio. O fallback por "pedido mais recente" só vale quando **não tinha identificador explícito nenhum** na mensagem nem no contexto ativo da conversa. Essa distinção é o cenário de isolamento da demo.
- `conversation_id` fornecido só pode retomar conversa que pertence ao JWT atual. ID desconhecido ou de outro cliente **vira conversa nova**, não erro — isso evita tanto leitura de cache alheio quanto overwrite por ID adivinhado.
- PII da mensagem é mascarada antes de qualquer coisa (`mask_pii`: e-mail, telefone, cartão, CPF). O que entra no prompt, no trace e no cache já é a versão mascarada.
- Ação administrativa (ligar/desligar agente, ver histórico de eval, ver guardrails, aprovar candidato, `/metrics`) exige header `X-Admin-Key`, comparado com `hmac.compare_digest`. Rota admin sem a chave responde 403, e isso é pra ser mostrado na demo, não escondido.
- As views de guardrail são admin porque expõem mensagem de **outros** clientes (tentativa de manipulação, PII mascarada). Não é dado de cliente comum.
- Conversa é limitada: 20 mensagens (`turns[-18:]` + as 2 do turno), TTL 24h, retomável por `GET /api/conversations/latest`. Esse endpoint precisa **replicar a timeline e o usage do último turno** a partir de `agent_traces`. Sem isso, sessão retomada mostra o texto certo com o raio-x vazio, e dá a impressão de que o multi-agent nunca rodou.
- `budget.py` impõe budget por agente **e** global por turno (`BudgetExceeded` → HTTP 429 com resposta parcial); `rate_limit.py` é limitador de janela deslizante por `ip:customer_key`; e o turno inteiro tem deadline global (`asyncio.wait_for`, 120s → 504).
- **Startup fail-closed.** Fora de `development`, o processo se recusa a subir se: `JWT_SECRET` ou `ADMIN_API_KEY` ainda for o valor de demo, os segredos tiverem menos de 32/24 caracteres, `AUTH_REQUIRED` estiver desligado, `DEMO_TOKEN_ISSUANCE_ENABLED` estiver ligado, ou `CORS_ORIGINS` for `*`. É o `validate_runtime_security()`, roda no `lifespan`, e tem teste parametrizado. Config insegura que sobe e "funciona" é o jeito mais fácil de vazar uma PoV pra internet.
- `/api/auth/token` só existe com `DEMO_TOKEN_ISSUANCE_ENABLED=1`, senão responde 404. Em ambiente real quem emite JWT é o IdP.
- O handler global de exceção nunca devolve exceção crua do driver. Devolve mensagem genérica + `request_id`, e o detalhe fica no log. O health também não vaza: em falha responde 503 com `{"status": "degraded"}`.

## Escritas reais

Sempre perguntam se os agentes escrevem de verdade. Escrevem, com superfície mínima:

- `order_agent` — atualiza `status`, restrito à allowlist `{processando, enviado, entregue, troca_solicitada, reembolsado}`, com o filtro reconstruído. A intenção sai de palavra-chave (`troca`/`trocar` → `troca_solicitada`, `reembolso`/`estornar` → `reembolsado`). E o handoff pós-escrita pro `billing_agent`/`logistics_agent` roda **independente de o status ter mudado neste turno**. Quando eu fiz depender da mudança no turno, o handoff sumia em silêncio se um turno anterior (ou um caso de eval) já tivesse virado o pedido. Quando o status já era o pedido, a resposta muda ("já está com status X") e o evento vira `read` no lugar de `write` — honesto dos dois lados.
- `support_agent` — abre `support_tickets` só em escalação explícita ("atendente", "chamado", "escalar", "falar com humano"). **Não** abre por "sem evidência no KB", porque o fallback de ranking local do `DEMO_MODE` sempre retorna *algum* artigo, relevante ou não.
- `loyalty_agent` — resgate real: `$inc` negativo em `loyalty_accounts.points`, restrito à tabela fixa `REWARD_CATALOG` (frete grátis 300, cupom 500, voucher 500), mais documento de auditoria em `redemptions`. Saldo insuficiente **nega e explica**, sem escrever nada. Resgate por produto vira handoff pro `product_agent`.
- `logistics_agent` — marca `shipments.reschedule_requested: true`. Campo único, nada além disso. Quem confirma a nova data é a transportadora; o sistema só registra a solicitação. E não reagenda o que já está "Entregue".

Nenhum desses valores vem do modelo. O modelo escreve a frase; a escrita é decidida por palavra-chave e executada por função Python com filtro reconstruído.

## Observabilidade ao vivo

`GET /api/events/stream` (SSE) em cima de um **Change Stream** em `agent_handoffs`, filtrado pras conversas do próprio chamador.

Em `DEMO_MODE` (ou se o `watch` falhar), cai pra polling de 1.2s com um set dos `_id` já vistos, limitado a 1000 entradas por um `deque` — sem esse limite, demo longa vaza memória devagarinho. **E o frontend não muda uma linha**, porque o formato do evento é o mesmo.

Todo `TimelineEvent` carrega um `op`: `read`, `write`, `vectorSearch`, `hybridSearch`, `changeStream`. Renderiza isso como painel "coleções em ação" por turno e acumula em contador `collection.<nome>.<op>` exposto em `GET /api/metrics`. É isso que transforma "o agente respondeu" em "o agente tocou estas coleções, nesta ordem, com estas operações".

Fora isso: `/metrics` em formato Prometheus (admin), latência média e p95 por rota com janela de 1000 amostras, `X-Request-Id` em toda requisição, log estruturado em JSON, e um hook opcional de Langfuse (`langfuse_client.log_cache_decision`) que registra HIT/MISS, fonte, score e tokens economizados por turno. Sem as chaves, vira no-op.

## Abstração de storage e `DEMO_MODE`

Faz um `DataStore` em `database.py` que alterna entre Atlas real e backend em memória via `DEMO_MODE` (ou ausência de `MONGODB_URI`), **com os mesmos contratos**: `find_one`, `find_many`, `count`, `insert_one`, `replace_one`, `update_one`, `delete_many`, `watch_handoffs`. É isso que permite `smoke.py`, `eval.py` e CI rodarem sem acesso ao cluster.

O backend em memória usa `deepcopy` na entrada e na saída (senão o chamador muta o "banco" por referência e você passa uma tarde caçando um bug que não existe), um `asyncio.Lock` global, e um `_matches` que entende `$gt/$gte/$lt/$lte/$in/$ne/$regex`. Nada além disso.

O `aggregate()` é a exceção, e é de propósito: **levanta `RuntimeError` em `DEMO_MODE`**. Pipeline de `$vectorSearch` não tem como ser simulado de forma honesta, então quem chama tem que tratar `store.memory` antes. Melhor estourar no desenvolvimento do que devolver um resultado inventado que parece busca vetorial.

O `count()` sem filtro usa `estimated_document_count()` (metadata, O(1)); com filtro, `count_documents`. Health check batendo `count_documents({})` em três coleções é scan completo três vezes por poll.

Em `DEMO_MODE` o próprio `lifespan` roda o seed na subida (`create_indexes=False`), então o servidor nasce pronto, sem passo manual.

## Portas e ambiente

Backend na **8031**, frontend na **5191**, as duas **estritas**: se estiver ocupada, o processo sai em vez de escorregar pra outra porta. No Vite usa `--strictPort` e trava em `127.0.0.1:5191`.

O motivo é bem prático: essa máquina roda várias PoVs ao mesmo tempo. Porta escorregando deixa o `VITE_API_URL` apontando pro lugar errado, e eu descubro isso na frente do cliente.

```
VITE_API_URL=http://127.0.0.1:8031
VITE_ADMIN_KEY=troque-a-chave-administrativa
```

O `.env` do backend fica na **raiz do projeto**, não dentro de `backend/` — o `config.py` resolve `parents[2]`. `pydantic-settings` com `extra="ignore"`, e `ENVIRONMENT` como alias explícito.

## Comandos que eu preciso ter

```bash
# setup
cp .env.example .env
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/seed.py

# backend
cd backend && python run.py
cd backend && DEMO_MODE=1 AUTH_REQUIRED=1 python run.py   # sem Atlas

# frontend
cd frontend && npm install && npm run dev

# testes e avaliação
cd backend && pytest -q
python backend/tests/smoke.py http://127.0.0.1:8031    # black-box, exit != 0 em falha
python backend/eval.py http://127.0.0.1:8031           # golden dataset -> eval_runs
cd backend && python calibrate_thresholds.py           # --apply grava vector_threshold
cd backend && ruff check .
cd frontend && npm run build
```

## Ordem de trabalho

1. ADR + modelagem das coleções de coordenação. Discute comigo antes de codar.
2. `DataStore` com os dois backends e os mesmos contratos.
3. Seed + índices, incluindo os vetoriais e os validadores de schema.
4. Roteamento determinístico, com teste, sem LLM nenhum envolvido.
5. Os oito agentes, cada um com sua superfície de escrita mínima.
6. Guardrail camada por camada, e só então o `calibrate_thresholds.py` medindo de verdade.
7. Cascata de cache.
8. Change Stream e SSE.
9. `eval.py` com golden dataset.
10. Frontend.

Não pula do passo 6 pro 7. Cache mascarando guardrail mal calibrado é o tipo de coisa que só aparece quando alguém tenta burlar ao vivo, e aí já era.

## Testes que eu quero ver existindo

Poucos e no lugar certo, cobrindo o que quebra de verdade:

- **Roteamento** — rota óbvia sem LLM, diagnóstico ganhando de recomendação, insensibilidade a acento.
- **Isolamento de cache** — intenção personalizada nunca vaza pro escopo global; curto prazo exige `customer_key` mesmo com `session_id` igual; cache global exige elegibilidade explícita; garantia nunca é global nem se o chamador pedir; `conversation_id` de outro cliente vira conversa nova em vez de sequestro; drift de índice cai no fallback sem derrubar o turno.
- **Políticas** — filtro reconstruído com o dono, status fora da allowlist rejeitado, `invoice_id` de outro dono nunca aceito.
- **Limites** — budget por agente e global, janela deslizante podando entrada velha.
- **Config de segurança** — configuração de produção segura aceita, e cada campo inseguro rejeitado (parametrizado).
- **RRF** — documento presente nos dois rankings sobe.
- **`smoke.py`** — black-box contra o servidor no ar, exit != 0 em falha.

CI roda os testes de backend e o build de produção do frontend em todo push/PR.

## Como quero que você trabalhe

- Documentação e texto de UI **em português**; código e comentário **em inglês**.
- Nada de documento inerte pra inflar contagem de nada.
- Quando a decisão for calibrável, **calibra e me mostra o número** — não escolhe um valor bonito.
- Se precisar de fallback, o fallback mantém os mesmos filtros de isolamento e o mesmo contrato de retorno. Fallback que relaxa segurança não é fallback.
- Todo ganho que entrar na documentação vem com a métrica que comprova ele.
- Comentário no código explica **por que**, não o que. Se um trecho existe porque uma abordagem anterior falhou, o comentário conta qual falhou — é isso que evita alguém "simplificar" de volta pro bug.

## Lacunas conhecidas — deixa registrado, não resolve

- Métrica é em processo e reseta no restart. Sem persistência nem agregação entre instâncias.
- Sem Docker e sem configuração de deploy. Desenvolvimento local, venv + npm, portas estritas. CI existe, mas só pra teste e build.
- Síntese por LLM e guardrail semântico custam token Anthropic real por turno. Aceitável pra demo; antes de volume de produção precisaria ajustar cache e amostragem.
- A extração de fato pra `customer_memory` é por palavra-chave, não por modelo. Cobre dois tipos de fato e assume português.
- O feed ao vivo mostra só o último handoff. Isso é decisão de apresentação, não limitação técnica — o Change Stream entrega todos.
