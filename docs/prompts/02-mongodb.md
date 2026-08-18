# Multi-Agent on MongoDB — MongoDB: bases, índices, embeddings e queries

> Segundo dos três prompts. O Atlas aqui é data plane e coordination plane ao mesmo tempo. Este arquivo mostra o que isso significa em coleção, índice, embedding e **query executada** — com o pipeline colado e o motivo de cada parâmetro.
>
> É o mais longo dos três de propósito: a tese é que orquestração de agente cabe num cluster e fica auditável por query. A query precisa estar escrita.

---

## Inventário de operadores — o que esta PoV usa contra o Atlas

Auditado no código em 2026-08-18, não de memória:

| Operador | Ocorrências | Onde |
|---|---|---|
| `$vectorSearch` | 15 | cascata de cache (2 níveis), guardrail semântico, memória longa, catálogo, KB |
| `$unionWith` | 3 | a cascata: curto prazo ∪ cache numa consulta só |
| `$search` (BM25) | 1 | perna lexical do híbrido de KB (`kb_lexical_v1`) |
| `$addFields` + `$multiply`/`$divide`/`$min` | — | ranking ponderado do catálogo, dentro da agregação |
| **`$regex` em query** | **0** | — |

`find`

`find` continua sendo usado, sempre em um destes papéis:

- **point lookup por índice**: `orders` por `order_id`, `invoices` por `invoice_id`, `loyalty_accounts`/`customers` por `customer_key`, `shipments` por `order_id` — todos com o `owner_customer_key` reconstruído junto;
- **listagem curta e ordenada** por índice composto (`(owner_customer_key, status)`, `(owner_customer_key, due_date)`);
- **leitura de configuração** no `multiagent_brain` (registry, regras de roteamento, políticas, cenários).

Isso é deliberado e vale defender em banca: trocar um lookup por chave por `$search` seria erro de arquitetura, e alguém que modela dado vai reparar. **O diferencial do MongoDB aqui não é "nunca usar `find`" — é o cluster ser data plane e coordination plane ao mesmo tempo**: cache semântico, guardrail por paráfrase, memória, roteamento, handoff e histórico de avaliação são todos documento, sem fila, sem workflow engine e sem vector DB ao lado.

---

## Duas bases no mesmo cluster

A separação é de propósito:

- **`multi_agent_poc`** — o dado do negócio e o rastro de execução: `customers`, `orders`, `invoices`, `products_catalog`, `kb_articles`, `warranty_policies`, `loyalty_accounts`, `shipments`, `support_tickets`, `redemptions`, `agent_conversations`, `agent_handoffs`, `agent_traces`, `customer_memory`, `short_term_memory`, `long_term_memory`, `semantic_cache`, `guardrail_denylist`, `guardrail_events`, `guardrail_candidates`, `admin_audit`, `eval_runs`.
- **`multiagent_brain`** — o cérebro configurável: `agent_registry`, `routing_rules`, `guardrail_policies`, `demo_scenarios`, `model_config`.

Tudo que lê do `multiagent_brain` passa pelo mesmo `DataStore` com `brain=True`. **Não cria um segundo cliente Mongo só pra isso.**

> **O nome do database do cérebro não pode ser genérico.** Ele já se chamou `ai_brain` — e o cluster é compartilhado com a PoV `singleagent`, que também tem um `ai_brain` com `guardrail_policies` e `model_config` de **schema diferente**. Rodar o seed de uma PoV sobrescrevia a política da outra, e o `/api/chat` passava a quebrar com `KeyError: 'threshold'` na primeira pergunta. Descoberto exatamente assim, na véspera de uma apresentação. Se você criar uma PoV nova neste cluster, dê ao cérebro dela um nome próprio.

O ponto dessa divisão: o que é configuração de orquestração (quem existe, como rotear, o que bloquear, o que demonstrar) fica separado do que é dado de cliente. Trocar o comportamento do sistema é `update_one` no `multiagent_brain`.

---

## Embeddings — autoEmbed, zero embedding no cliente

**Nenhuma linha desta PoV chama uma API de embedding.** Todos os vetores são gerados pelo Atlas, no write e na query.

| Item | Valor |
|---|---|
| Modelo | `voyage-4` |
| Modalidade | `text` |
| `numDimensions` | **1024** |
| `similarity` | `cosine` |
| `indexingMethod` | `flat` |

Isso vale para os **oito** índices vetoriais, sem exceção — mesma configuração em todos, pra que o comportamento de score seja comparável entre camadas.

No `$vectorSearch` a consulta vai como `"query": {"text": message}` com `"model": "voyage-4"` — texto cru, vetorizado no servidor. Não existe `queryVector` em lugar nenhum do código.

### O que a escala de score realmente é — e não é

Isso foi medido no índice real, não tirado de tabela:

> Com `voyage-4` autoEmbed e quantização escalar, **texto idêntico chega a ~0.84, não a 1.0**, e não-relacionado mede ~0.64.

Um threshold "de catálogo" tipo 0.85 nunca ia bater nem no caso trivial.

Medição de 18/08/2026, no índice em uso:

| | banda |
|---|---|
| texto **idêntico** | 0.8101 – 0.9213 (frase curta fica na faixa baixa) |
| pergunta **não relacionada** | 0.6453 – 0.7545 |

A folga real é de ~0.056 entre o pior negativo e o menor idêntico — e é daí que saem os **0.78/0.80** da cascata. Os valores anteriores (0.80/0.83) ficavam **acima** do menor idêntico, então repetir uma pergunta curta numa conversa nova dava MISS: justamente o beat de cache da demo.

---

## Os oito índices vetoriais

Declarados em `backend/seed.py:create_search_indexes()`.

| Índice | Coleção | `path` (o que é embedado) | Campos `filter` |
|---|---|---|---|
| `products_autoembed_v1` | `products_catalog` | `search_text` | `category`, `active`, `price` |
| `kb_autoembed_v1` | `kb_articles` | `content` | `category` |
| `memory_autoembed_v1` | `customer_memory` | `fact` | `customer_key`, `active` |
| `cache_autoembed_v1` | `semantic_cache` | `question_text` | `agent`, `area`, `customer_key`, `scope` |
| `short_term_autoembed_v1` | `short_term_memory` | `question_text` | `session_id`, `customer_key`, `agent` |
| `denylist_autoembed_v1` | `guardrail_denylist` | `phrase` | `area`, `active`, `layer` |
| `long_term_autoembed_v1` | `long_term_memory` | `text` | `customer_key` |

Mais **um índice lexical**:

| Índice | Coleção | Definição |
|---|---|---|
| `kb_lexical_v1` | `kb_articles` | `title` e `content` como `string` com `analyzer: "lucene.portuguese"`; `category` como `token`; `dynamic: False` |

`lucene.portuguese` porque a base de conhecimento é em português e stemming errado degrada o BM25 em silêncio. `category` como `token` porque dela eu quero `equals` exato, não texto analisado.

### Os campos `filter` são o isolamento

O `$vectorSearch` aplica o filtro **durante** a busca ANN. O grafo só percorre vetores aplicáveis, então o top match é sempre válido — não importa quanto a coleção cresça.

Três casos onde isso deixa de ser detalhe:

- **`cache_autoembed_v1` tem quatro filtros** (`agent`, `area`, `customer_key`, `scope`) porque o cache tem quatro dimensões de isolamento ao mesmo tempo: quem respondeu, qual área pode ver, de quem é, e se é público ou pessoal.
- **`denylist_autoembed_v1` filtra por `layer`** — e essa é a decisão mais contraintuitiva do projeto. As entradas **lexicais** são fragmentos curtos (`"sem nota fiscal"`) que, como vetor, ficam colados numa pergunta legítima (`"pode me enviar a nota fiscal da minha compra?"` — **medido em 0.8263**, acima de ataque real). Elas servem pra substring; a busca vetorial só percorre as frases escritas como **intenção completa**. Sem o filtro `layer`, o guardrail vira uma máquina de falso positivo.
- **`memory_autoembed_v1` filtra `active`** — fato superseded nunca entra no ranking, então não pode ser descartado tarde demais, depois que o `limit` já cortou o que interessava.

Se o índice já existe com outra definição, chama `update_search_index` em vez de falhar. **Rodar o seed duas vezes não pode quebrar nada.**

---

## Índices regulares, únicos e TTL

Definidos em `app/database.py:create_standard_indexes()`.

```python
"customers":            [("customer_key", 1)]                                   # único
"orders":               [("order_id", 1)] (único), [("owner_customer_key", 1), ("status", 1)]
"invoices":             [("invoice_id", 1)] (único), [("owner_customer_key", 1), ("due_date", 1)]
"loyalty_accounts":     [("customer_key", 1)]                                   # único
"shipments":            [("order_id", 1)] (único), [("owner_customer_key", 1)]
"warranty_policies":    [("category", 1)]                                       # único
"agent_conversations":  [("conversation_id", 1)] (único), [("updated_at", 1)]   # TTL 24h
"customer_memory":      [("customer_key", 1), ("active", 1)]
"agent_handoffs":       [("conversation_id", 1), ("at", 1)], [("at", 1)]        # TTL 30d
"agent_traces":         [("conversation_id", 1), ("at", 1)], [("at", 1)]        # TTL 30d
"semantic_cache":       [("agent", 1), ("area", 1)], [("expires_at", 1)]        # TTL 0
"short_term_memory":    [("session_id", 1)], [("expires_at", 1)]                # TTL 0
"long_term_memory":     [("customer_key", 1)]
"guardrail_denylist":   [("phrase_norm", 1)]                                    # único
"guardrail_events":     [("at", 1)]                                             # TTL 30d
"guardrail_candidates": [("status", 1), ("created_at", 1)]
"admin_audit":          [("at", 1)]                                             # TTL 30d
"eval_runs":            [("at", 1)]                                             # TTL 90d
"support_tickets":      [("customer_key", 1), ("created_at", 1)]
"redemptions":          [("customer_key", 1), ("at", 1)]
```

Racional, resumido:

- Os **únicos são invariantes de domínio**, não otimização: um cliente, um pedido, uma fatura, uma conta de fidelidade, uma política por categoria. `guardrail_denylist.phrase_norm` único impede a mesma frase entrar duas vezes com grafia diferente e pontuar em dobro.
- **`(owner_customer_key, …)` em `orders`, `invoices` e `shipments`** — o dono vem primeiro no índice porque toda query de negócio é filtrada por ele. É o índice que torna o isolamento barato, não só correto.
- **`(customer_key, active)`** em `customer_memory` — a leitura mais frequente da memória de fatos.
- **`(conversation_id, at)`** em handoffs e traces — a Timeline da UI, na ordem.

### TTL

| Coleção | Campo | Prazo |
|---|---|---|
| `semantic_cache`, `short_term_memory` | `expires_at` | `expireAfterSeconds: 0` (o documento carrega a data, 24h à frente) |
| `agent_conversations` | `updated_at` | 24h |
| `agent_handoffs`, `agent_traces`, `guardrail_events`, `admin_audit` | `at` | 30 dias |
| `eval_runs` | `at` | 90 dias |

Telemetria e auditoria de PoV não crescem pra sempre. E o cache com `expireAfterSeconds: 0` deixa **o frescor por conta do banco**, não da aplicação.

---

## Validadores `$jsonSchema`

Em `agent_handoffs` e `agent_traces`, com `validationLevel="moderate"` e `validationAction="error"` (no-op em `DEMO_MODE`):

```python
"agent_handoffs": {"$jsonSchema": {
    "bsonType": "object",
    "required": ["conversation_id", "from_agent", "to_agent", "reason", "at"],
    "properties": {
        "conversation_id": {"bsonType": "string", "minLength": 4},
        "customer_key":    {"bsonType": "string"},
        "from_agent":      {"bsonType": "string"},
        "to_agent":        {"bsonType": "string"},
        "reason":          {"bsonType": ["string", "null"]},
        "at":              {"bsonType": "date"},
    }}}

"agent_traces": {"$jsonSchema": {
    "bsonType": "object",
    "required": ["conversation_id", "customer_key", "active_agent", "at"],
    …}}
```

Aplicado por `collMod`, com fallback pra `create_collection`. Eu quero o **próprio MongoDB** rejeitando documento malformado, não só a camada Python. É o controle que arquitetura multi-agente equivalente em outra stack resolve com **schema registry externo** — aqui é um comando no banco.

E repara no `reason` aceitando `["string", "null"]`: handoff sem motivo é possível, handoff sem `from`/`to` não é. O validador diz qual é qual.

---

## As queries, uma a uma

### 1. A cascata de cache — uma consulta só decide HIT/MISS

Esta é a query mais importante da PoV. Ela roda **antes de qualquer chamada de LLM**.

```python
[
  # nível 1 — curto prazo: reformulação da mesma pergunta, nesta sessão
  {"$vectorSearch": {
      "index": "short_term_autoembed_v1", "path": "question_text",
      "query": {"text": message}, "model": "voyage-4",
      "filter": {"session_id": session_id, "customer_key": customer_key, "agent": target},
      "numCandidates": 50, "limit": 5}},
  {"$addFields": {"score": {"$meta": "vectorSearchScore"}, "fonte": "curto_prazo"}},
  {"$match": {"score": {"$gte": 0.78}}},          # threshold PERMISSIVO
  {"$sort": {"score": -1}},
  {"$limit": 1},

  # nível 2 — cache: pergunta comum já respondida
  {"$unionWith": {"coll": "semantic_cache", "pipeline": [
      {"$vectorSearch": {
          "index": "cache_autoembed_v1", "path": "question_text",
          "query": {"text": message}, "model": "voyage-4",
          "filter": {"$or": [
              {"scope": "global",   "area": area,                  "agent": target},
              {"scope": "customer", "customer_key": customer_key,  "agent": target}]},
          "numCandidates": 50, "limit": 5}},
      {"$addFields": {"score": {"$meta": "vectorSearchScore"}, "fonte": "cache"}},
      {"$match": {"score": {"$gte": 0.80}}},      # threshold RÍGIDO
      {"$sort": {"score": -1}},
      {"$limit": 1},
  ]}},

  {"$sort": {"score": -1}},
  {"$limit": 1},
]
```

**Cada ramo filtra pelo próprio threshold ANTES do union.** Se você deixar o filtro pra depois, um score de cache abaixo do threshold rígido dele pode ganhar o `$sort` só por ser maior que o corte permissivo do curto prazo. **Isso já quebrou aqui.**

O `$or` dentro do filtro do nível 2 é o que expressa as duas visibilidades numa consulta só: entrada `global` é vista por qualquer cliente **da mesma área e do mesmo agente**; entrada `customer` só pelo dono.

Os números 0.78/0.80 saíram da medição descrita lá em cima. Permissivo no curto prazo (é a mesma pessoa, na mesma conversa, reformulando), rígido no cache (é resposta de outra pessoa sendo reaproveitada).

**E o corte não é a última palavra.** Quando o `$vectorSearch` não acha nada acima do limiar, a cascata cai no match exato por `question_norm` — determinístico, mesmos filtros de isolamento. Texto literalmente idêntico **sempre** dá HIT, independente de score. Antes esse fallback só rodava quando o `$vectorSearch` lançava exceção; agora roda também no MISS, que é o caso comum.

**Fallback:** se o `$vectorSearch` estourar (índice construindo, drift de definição), cai pra match exato por `question_norm` com **os mesmos filtros de isolamento**, mantendo o contrato de retorno idêntico (`hit`/`fonte`/`score`, score fixo em 1.0) e a mesma prioridade curto prazo → cache. Atendimento não pode cair porque um índice está construindo. Tem teste: `test_atlas_index_drift_falls_back_without_breaking_the_turn`.

### 2. Memória de longo prazo — o input do prompt

```python
[
  {"$vectorSearch": {
      "index": "long_term_autoembed_v1", "path": "text",
      "query": {"text": message}, "model": "voyage-4",
      "filter": {"customer_key": customer_key},
      "numCandidates": 50, "limit": <long_term_memory_limit>}},
  {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
]
```

Isso **não é resposta pronta**, é input pro prompt — por isso não conta como cache hit. Falha do índice degrada pra `find_many` por `customer_key`: a memória enriquece o turno, não pode derrubá-lo, e o isolamento continua o mesmo nos dois caminhos.

### 3. As escritas da cascata — `cascade_store_turn()`

Três `replace_one` com `upsert=True`, e a diferença entre eles é o argumento inteiro do escopo de cache:

```python
# sempre: curto prazo, chaveado por sessão
{"session_id": …, "customer_key": …, "agent": target, "question_norm": …}

# sempre: cache pessoal — cobre repetir a pergunta numa conversa NOVA
{"agent": target, "customer_key": …, "scope": "customer", "question_norm": …}

# só quando elegível: cache público
{"agent": target, "area": area, "scope": "global", "question_norm": …}
```

Todos gravam `expires_at = now + 24h`, e o documento carrega `answer`, `active_agent` e **a cauda da timeline** do turno — é isso que faz o HIT reproduzir o raio-x completo na UI em vez de mostrar uma bolha de texto solta.

O escopo `global` exige que **intenção E evidências** provem que a resposta é pública: intenção em `GLOBAL_CACHE_INTENTS` (catálogo e KB), nenhum uso de memória do cliente, nenhum longo prazo recuperado, nenhum fato novo escrito, nenhum handoff, mesmo agente do começo ao fim, **nenhum evento com `op == "write"`** — e o chamador precisa optar explicitamente (`global_eligible=True`).

E `cascade_store_episode()` grava o episódio de longo prazo:

```python
{"customer_key": …, "text": f"Pergunta: {message}\nResposta: {answer}", "created_at": now}
```

Essa função existe porque **`cascade_long_term_context()` já lia dali e nada escrevia** — a collection ficava sempre vazia e o painel de governança mentia sobre a terceira camada da cascata.

### 4. Guardrail semântico

```python
[
  {"$vectorSearch": {
      "index": "denylist_autoembed_v1", "path": "phrase",
      "query": {"text": message}, "model": "voyage-4",
      "filter": {"area": {"$in": ["global", area]}, "active": True, "layer": "semantic"},
      "numCandidates": 50, "limit": 1}},
  {"$project": {"phrase": 1, "category": 1, "area": 1,
                "score": {"$meta": "vectorSearchScore"}}},
]
```

Por que essa camada existe, em uma frase: **Jaccard sobre palavras não separa paráfrase de pergunta legítima** — "quero ver dados de outro comprador" e "pode me enviar a nota fiscal" pontuam praticamente igual. Só a busca vetorial dá esse sinal, e dá **sem custo de LLM**.

O `filter` carrega os três recortes: área aplicável, entrada ativa, e `layer: "semantic"` (o motivo está lá em cima, nos índices).

Exceção → `disponível=False`, que significa "a camada não pôde rodar", **não "liberado"**. Quem decide o que fazer com isso é o `semantic_fail_mode` da política da área, não o helper.

### 5. Catálogo — ranking ponderado numa agregação só

```python
[
  {"$vectorSearch": {
      "index": "products_autoembed_v1", "path": "search_text",
      "query": {"text": message}, "model": "voyage-4",
      "filter": {"active": True,                       # + price/category quando houver
                 "price": {"$lt": max_price},
                 "category": category},
      "numCandidates": 50, "limit": 8}},
  {"$addFields": {"relevance": {"$meta": "vectorSearchScore"}}},
  {"$addFields": {"weighted_score": {"$add": [
      {"$multiply": [0.55, "$relevance"]},
      {"$multiply": [0.30, {"$divide": ["$rating", 5.0]}]},
      {"$multiply": [0.15, {"$divide": [{"$min": ["$stock", 20]}, 20.0]}]},
  ]}}},
  {"$sort": {"weighted_score": -1}},
  {"$limit": 4},
  {"$project": {"_id": 0, "sku": 1, "name": 1, "category": 1, "price": 1,
                "rating": 1, "stock": 1, "relevance": 1, "weighted_score": 1}},
]
```

Relevância **0.55** + nota **0.30** + estoque **0.15**, tudo normalizado (nota sobre 5, estoque saturado em 20). Recomendar um produto ótimo que está sem estoque é um problema de negócio, não de busca — por isso o estoque entra no score, e satura: 40 unidades não é melhor que 20.

O ranking numa agregação só é proposital: eu quero mostrar o pipeline inteiro na tela e dizer **"isso aqui é uma query, não é um serviço de ranking"**. E os filtros são nativos do índice, então o teto de preço não é aplicado depois de o `limit` já ter cortado.

Busca de 8 e devolve 4: a folga existe pra que a reponderação tenha o que reordenar.

### 6. Base de conhecimento — híbrido com RRF

Duas queries em paralelo (`asyncio.gather`) sobre `kb_articles`:

```python
# perna vetorial
[{"$vectorSearch": {"index": "kb_autoembed_v1", "path": "content",
                    "query": {"text": message}, "model": "voyage-4",
                    "numCandidates": 50, "limit": 10}},
 {"$project": {"article_id": 1, "title": 1, "content": 1, "category": 1}}]

# perna lexical (BM25)
[{"$search": {"index": "kb_lexical_v1", "compound": {
    "should": [
        {"text": {"query": message, "path": "title",
                  "score": {"boost": {"value": 2}}}},     # título pesa o dobro
        {"text": {"query": message, "path": "content"}},
    ],
    "minimumShouldMatch": 1}}},
 {"$limit": 10},
 {"$project": {"article_id": 1, "title": 1, "content": 1, "category": 1}}]
```

Fundidos por `reciprocal_rank_fusion([vector, lexical], limit=4)`:

```python
score(doc) = Σ 1 / (k + posição),   k = 60
```

**O RRF existe porque os dois rankings têm escala incomparável.** Somar score de BM25 com score de cosseno é errado, e o pior é que dá um resultado que parece funcionar até o dia que não funciona.

O `boost: 2` no título é regra de domínio: em base de conhecimento, o título é o resumo da intenção do artigo.

A chave da fusão é `article_id` copiado pra `_id` antes de fundir — os dois pipelines projetam o mesmo campo pra que documento presente nos dois rankings seja reconhecido como o mesmo. Tem teste pra isso.

### 7. Memória de fatos — supersessão, não update

```python
# supersessão: o fato antigo é DESATIVADO, não sobrescrito
existing = find_many("customer_memory",
                     {"customer_key": …, "fact_type": fact_type, "active": True}, limit=10)
for fact in existing:
    update_one("customer_memory", {"_id": fact["_id"]},
               {"$set": {"active": False, "superseded_at": utcnow()}})
# ... e entra um documento novo

# leitura
find_many("customer_memory", {"customer_key": …, "active": True}, limit=20)
```

Preserva a trilha de auditoria e permite mostrar na UI que o fato foi **substituído, não sobrescrito**. Os dois filtros batem exatamente no índice `(customer_key, active)`.

### 8. As escritas reais dos agentes

Superfície mínima, cada uma numa coleção só:

```python
# order_agent — status, restrito à allowlist
update_one("orders", <filtro reconstruído>, {"$set": {"status": <allowlist>}})

# loyalty_agent — resgate: débito + auditoria
update_one("loyalty_accounts", query, {"$inc": {"points": -cost}})
insert_one("redemptions", redemption)

# logistics_agent — campo único
update_one("shipments", query, {"$set": {"reschedule_requested": True}})

# support_agent — só em escalação explícita
insert_one("support_tickets", ticket)
```

**Nenhum desses valores vem do modelo.** O modelo escreve a frase; a escrita é decidida por palavra-chave e executada por função Python com o filtro **reconstruído** no servidor (`app/policies.py`):

```python
safe_order_read_filter  → {"order_id": <validado>,   "owner_customer_key": <do JWT>}
safe_invoice_filter     → {"invoice_id": <validado>, "owner_customer_key": <do JWT>}
safe_shipment_filter    → {"order_id": <validado>,   "owner_customer_key": <do JWT>}
safe_order_update       → {"$set": {"status": <um da allowlist>}}
```

O `owner_customer_key` nunca vem do payload — sai do JWT e é remontado. `order_id`/`invoice_id` passam por regex antes.

### 9. Change Stream — o feed ao vivo

```python
collection("agent_handoffs").watch(
    [{"$match": {"operationType": "insert", "$or": [
        {"fullDocument.customer_key": customer_key},
        {"fullDocument.customer_key": {"$exists": False}},   # legado
    ]}}],
    full_document="updateLookup",
)
```

O **`customer_key` é denormalizado no documento de handoff** justamente pra que o filtro de dono rode **server-side, no próprio `$match` do Change Stream** — sem um `find_one` por evento. Documento legado sem o campo cai num fallback que valida o dono pela conversa.

Em `DEMO_MODE` (ou se o `watch` falhar), vira polling de 1.2s com um set de `_id` já vistos, limitado a 1000 entradas por um `deque` — sem esse limite, demo longa vaza memória devagarinho. **E o frontend não muda uma linha**, porque o formato do evento é o mesmo.

---

### 10. Orientação — o retrato do cliente (`guidance.py`)

Quatro leituras curtas, todas filtradas por dono, que alimentam as sugestões de próximo passo e as respostas de "não encontrei":

```python
find_many("orders",    {"owner_customer_key": owner}, limit=3, sort=[("order_id", -1)])
find_many("invoices",  {"owner_customer_key": owner}, limit=3, sort=[("due_date", -1)])
find_one ("loyalty_accounts", {"customer_key": owner})
find_many("shipments", {"owner_customer_key": owner}, limit=3)
```

Cada uma bate exatamente num índice composto já existente. Falha de qualquer uma degrada para lista vazia — orientação é auxiliar e nunca derruba o turno que a chamou.

**Melhoria conhecida:** são quatro idas ao servidor onde caberia **uma agregação só**, com `$unionWith` ou `$facet` atravessando as coleções. Fica registrado como próximo passo — e é um beat de demo por si (*"quatro coleções, uma consulta"*).

## Os limiares — medidos, não escolhidos

| Onde | Campo | Valor | O que é |
|---|---|---|---|
| `app/config.py` | `short_term_cache_threshold` | **0.78** | corte permissivo do nível 1 |
| `app/config.py` | `global_cache_threshold` | **0.80** | corte rígido do nível 2 |
| `multiagent_brain.guardrail_policies` (area `default`) | `vector_threshold` | **0.7791** | denylist semântica |
| `multiagent_brain.guardrail_policies` (area `financeiro`) | `vector_threshold` | **0.7791** | idem, com `threshold` lexical mais rígido (0.82 contra 0.86) |
| ambas | `semantic_fail_mode` | `closed` | camada semântica fora ⇒ bloqueia pelo caminho lexical |

O `threshold` (0.86 / 0.82) é **Jaccard lexical**, e ele existe só como fallback do `DEMO_MODE`/CI. Com o vetorial no ar ele vira ruído — por isso o score que aparece no painel é o **vetorial** quando existe. Mostrar 0.1 de Jaccard numa frase que o guardrail avaliou em 0.77 dá a impressão de que ele não viu nada.

Quem mede é o `backend/calibrate_thresholds.py`, com 12 sondas rotuladas `(deve_bloquear, texto, area)` e **o mesmo pré-filtro do runtime**. Ele calcula `max(negativos)` e `min(positivos)` e sugere o ponto médio.

Duas regras que precisam ser mantidas:

- **As sondas positivas são paráfrases, nunca quase-cópias da frase seedada.** Calibrar com quase-cópia fixa o limiar na banda de "texto idêntico" e o guardrail volta a ser casamento exato — a camada semântica morre e ninguém percebe.
- **As entradas lexicais ficam fora do índice vetorial, via filtro `layer`.** (O 0.8263 da nota fiscal.)

Se não houver separação (`max(negativos) >= min(positivos)`), ele **se recusa a sugerir** e manda cobrir a intenção do positivo com mais uma entrada seedada — baixar o threshold na mão só troca falso-negativo por falso-positivo. Threshold por área só é gravado quando aquela área tem sonda dos dois lados.

Recalibrar é `update_one`, não deploy — mesma história do `model_config`.

---

## `aggregate()` estoura em `DEMO_MODE`, de propósito

O `DataStore` em memória implementa `find_one`, `find_many`, `count`, `insert_one`, `replace_one`, `update_one`, `delete_many` e `watch_handoffs` com os mesmos contratos. Mas o `aggregate()` **levanta `RuntimeError`**.

Pipeline de `$vectorSearch` não tem como ser simulado de forma honesta, então quem chama tem que tratar `store.memory` antes — e é por isso que `search_products`, `search_kb` e o guardrail semântico começam com `if not store.memory:`. Melhor estourar no desenvolvimento do que devolver um resultado inventado que parece busca vetorial.

O `count()` sem filtro usa `estimated_document_count()` (metadata, O(1)); com filtro, `count_documents`. Health check batendo `count_documents({})` em três coleções é scan completo três vezes por poll.

---

## Seed, warmup e eval

### O seed invalida o cache — e isso não é opcional

Primeira coisa que o `seed.py` faz: **apagar `semantic_cache` e `short_term_memory`.**

O seed redefine o mundo (status de pedido, fatura, saldo de pontos). Toda resposta em cache foi derivada do mundo **anterior**. Sem essa limpeza, o turno seguinte serve um HIT afirmando "seu pedido está em `troca_solicitada`" enquanto a coleção já voltou pra `processando` — a demo se contradiz na tela, e se contradiz com confiança.

Isso apareceu quebrando a PoV de propósito: dois casos do `eval.py` falhavam porque o cache respondia sobre o estado antigo, sem tocar em `orders`. Depois da invalidação, **28/28**.

---

O `seed.py` é **idempotente** — `replace_one(..., upsert=True)` por chave natural (`customer_key`, `order_id`, `sku`, `article_id`, `phrase_norm`…). Ele cria os índices B-tree/únicos/TTL, aplica os validadores `$jsonSchema` e declara os oito índices vetoriais mais o lexical.

`multiagent_brain.model_config` nasce com `{"key": "default", "default_model": "claude-haiku-4-5", "global_turn_tokens": 20000}` — o modelo default é dado, não constante de código.

`backend/warmup.py` roda antes de demo ao vivo: chama os prompts marcados com `warmup: true`, uma vez por identidade, **de verdade, contra a Anthropic**, lendo de `DEMO_SCENARIOS` — a mesma fonte da UI, então não existe divergência de texto pra invalidar a chave de cache (que é a mensagem normalizada).

Isso não é uso fabricado: o primeiro turno real já aconteceu no warmup, então o clique ao vivo é um `cache_hit: true` genuíno reproduzindo a timeline armazenada. O TTL de 24h existe pra sobreviver da preparação até a reunião com folga.

O `eval.py` roda os mesmos cenários como golden dataset e checa, por caso: bloqueado ou não, `route_source`, **a sequência exata de agentes** (deduplicada por adjacência), quantos handoffs, qual collection foi escrita e se teve revisita. Grava tudo em `eval_runs` com `pass_rate` e sai com código != 0 se algum caso falhar. Métrica de qualidade morando no mesmo banco do resto é consultável como qualquer outro dado operacional.
