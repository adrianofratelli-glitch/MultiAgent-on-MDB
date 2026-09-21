# Graph Report - multiagente-atendimento  (2026-09-21)

## Corpus Check
- 13 files · ~187,716 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1539 nodes · 3176 edges · 129 communities (89 shown, 38 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 189 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Demo Reset & Episodic Memory
- Semantic Cache Cascade
- Warmup, Demo Reset & Chips Concepts
- Frontend API & App Shell
- Agent Registry & KB Search Concepts
- Guardrails (Two-Band)
- Product Search & Budget Pre-filter
- Settings & Config
- Scope Integration Tests
- Turn Classifier & Probes
- Agent Runners
- Greeting & Capability Detection
- ADR Set 001-004 (PT)
- Decisions & Audit
- Policies & Safe Filters
- Auto-Warmup Service
- UI Screens & Design
- Guidance & Welcome Replies
- Calibration Tests
- Replacement Chain
- LLM Gateway
- Orchestration Service
- Situations Eval & Generator Concepts
- Agent Memory Concepts
- Runtime Config
- API Routes (main.py)
- Resilience E2E Tests
- Frontend Dependencies
- Threshold Calibration
- Route Handlers
- Orchestration & Scope Gate
- Calibration & Scope Config Concepts
- DataStore Internals
- Scope Classifier Concepts
- ADR-003/004 Security Concepts
- Token Budget
- Models & Requests
- Scope Classifier Tests
- Agent Registry & Fan-out
- Handoff & Routing Concepts
- DataStore & Transactions
- Scope Classifier (Embedding)
- Replacement Chain Tests
- Langfuse Tracing
- ADR Set 001-004 (EN)
- Budget & Cascade Concepts
- Security & Auth
- Out-of-Scope Replies (Word List)
- Seed Data & Demo Scenarios
- Legacy Memory Migration
- Calibrator Bug & Dataset Growth
- ADR Set (Mirror)
- Long-Term Context
- Cost Economics
- Hybrid KB Retrieval (RRF)
- App Lifespan
- LLM Circuit Breaker
- Live Event Stream (SSE)
- Situations Eval Harness
- ADR-004 Baseline & Decisions
- Cache & Routing Principles
- LLM Cost Models
- LIVE Suites & Pre-push
- Concurrency Tests
- LIVE Random Tests
- Replacement Chain (graph.py)
- Architecture Components
- Misc 67
- Misc 68
- Misc 69
- Misc 70
- Misc 71
- Misc 72
- Misc 73
- Misc 74
- Misc 75
- Misc 76
- Misc 77
- Misc 78
- Misc 79
- Misc 80
- Misc 81
- Misc 82
- Misc 83
- Misc 84
- Misc 85
- Misc 86
- Misc 87
- Misc 88
- Misc 89
- Misc 90
- Misc 92
- Misc 93
- Misc 94
- Misc 95
- Misc 96
- Misc 97
- Misc 98
- Misc 99
- Misc 100
- Misc 101
- Misc 102
- Misc 103
- Misc 104
- Misc 105
- Misc 106
- Misc 107
- Misc 108
- Misc 109
- Misc 110
- Misc 112
- Misc 113
- Misc 114
- Misc 115
- Misc 116
- Misc 117
- Misc 118
- Misc 119
- Misc 120
- Misc 121
- Misc 122
- Misc 123
- Misc 124
- Misc 125
- Misc 126
- Misc 127
- Misc 128

## God Nodes (most connected - your core abstractions)
1. `DataStore` - 170 edges
2. `Settings` - 84 edges
3. `utcnow()` - 47 edges
4. `OrchestrationService` - 38 edges
5. `cascade_lookup()` - 33 edges
6. `get_settings()` - 31 edges
7. `active_budget()` - 25 edges
8. `world()` - 25 edges
9. `record_decision()` - 24 edges
10. `LLMGateway` - 22 edges

## Surprising Connections (you probably didn't know these)
- `Handoff loop MAX_HOPS=5` --semantically_similar_to--> `MAX_HOPS = 5 handoff loop`  [INFERRED] [semantically similar]
  docs/briefing/architecture.md → CLAUDE.md
- `Parallel fan-out` --semantically_similar_to--> `Parallel fan-out order_agent + billing_agent`  [INFERRED] [semantically similar]
  docs/briefing/architecture.md → CLAUDE.md
- `turn_classifier.py` --semantically_similar_to--> `turn_classifier (threshold 0.7162)`  [INFERRED] [semantically similar]
  docs/briefing/architecture.md → CLAUDE.md
- `scope_classifier.py` --semantically_similar_to--> `scope_classifier.py (in/out/chat)`  [INFERRED] [semantically similar]
  docs/briefing/architecture.md → CLAUDE.md
- `eval_situations.py / generate_situations.py` --semantically_similar_to--> `situations.json (287 cases / 39 categories)`  [INFERRED] [semantically similar]
  docs/briefing/architecture.md → CLAUDE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Grove cost capture -> LLM_BLENDED_PRICES -> eval cost reporting** — docs_internal_grove_cost_guide_regra_vigente_19_09, docs_agent_quality_economics_llm_blended_prices, docs_agent_quality_economics_eval_py, docs_agent_quality_economics_ledger_de_chamadas [EXTRACTED 0.90]
- **Taxonomia de Agent Memory: short-term + long-term + shared coordenados pelo recall()** — docs_decks_pov_agent_memory_mongodb_template_shorttermmemory, docs_decks_pov_agent_memory_mongodb_template_longtermmemory, docs_decks_pov_agent_memory_mongodb_template_sharedmemory, docs_decks_pov_agent_memory_mongodb_template_recallcascade [EXTRACTED 1.00]
- **Fluxo de um turno: politica -> recall -> contexto -> handoff -> registro sobre dois planos com TTLs distintos** — docs_decks_pov_memoria_multi_agente_turnmap, docs_decks_pov_memoria_multi_agente_twoplanes, docs_decks_pov_memoria_multi_agente_ttlladder, docs_decks_pov_memoria_multi_agente_orchestratorchains [EXTRACTED 1.00]
- **Shared dark green/monospace design system: nav shell, eyebrow + big claim headline, card grid** — docs_screenshots_01_chat_home_agent_control_plane_shell, docs_screenshots_04_agents_registry_agent_cards, docs_screenshots_05_metrics_kpi_tiles, docs_screenshots_06_guardrails_raw_json_audit [INFERRED 0.85]
- **MongoDB-as-coordination-plane evidence: handoff chain, collection ops, change stream, guardrail audit docs** — docs_screenshots_03_chain_timeline_agents_in_action_strip, docs_screenshots_03_chain_timeline_collections_in_action, docs_screenshots_03_chain_timeline_last_handoff_change_stream, docs_screenshots_05_metrics_collections_table, docs_screenshots_06_guardrails_raw_json_audit [INFERRED 0.85]
- **Five-step README demo narrative: empty chat, chain timeline, registry, metrics, guardrails** — docs_screenshots_01_chat_home_screenshot, docs_screenshots_03_chain_timeline_screenshot, docs_screenshots_04_agents_registry_screenshot, docs_screenshots_05_metrics_screenshot, docs_screenshots_06_guardrails_screenshot [INFERRED 0.95]
- **Scope classification pipeline** — docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_scope_classifier, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_scope_probes, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_scope_probes_vs, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_scope_classifier_config, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_calibrate_thresholds [EXTRACTED 1.00]
- **Situation-based measurement loop** — docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_generate_situations, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_verifier, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_situations, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_dev_holdout_split, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_eval_situations [EXTRACTED 1.00]
- **Guardrail defense layers** — claude_static_denylist, claude_denylist_autoembed, claude_llm_classifier, claude_two_band_guardrail, claude_needs_security_review [EXTRACTED 1.00]

## Communities (129 total, 38 thin omitted)

### Community 0 - "Demo Reset & Episodic Memory"
Cohesion: 0.06
Nodes (82): cascade_store_episode(), Registra na memória de longo prazo QUE o cliente tratou de um assunto — não o…, Reset da memória DA DEMO de um cliente: deixa o usuário como estava antes de a…, reset_customer_memory(), active_budget(), _active_docs(), active_facts(), _clean_budget() (+74 more)

### Community 1 - "Semantic Cache Cascade"
Cohesion: 0.09
Nodes (41): cascade_lookup(), cascade_store_turn(), is_compound_of(), looks_like_action_request(), Grava sempre em curto_prazo e só promove respostas estáveis ao cache semântico.…, Cascata com bypass de turno pessoal: uma resposta que depende da memória do…, fold(), Minúsculas, sem acento, pontuação → espaço, com sentinelas de borda. (+33 more)

### Community 2 - "Warmup, Demo Reset & Chips Concepts"
Cohesion: 0.05
Nodes (43): Auto-warmup (warmup.py), Demo reset (POST /api/demo/reset), MEMORY_DEMOS chips, migrate_legacy_memory.py, Auto-warmup (warmup.py), customer_memory + supersession, Demo reset (POST /api/demo/reset), MEMORY_DEMOS chips (+35 more)

### Community 3 - "Frontend API & App Shell"
Cohesion: 0.06
Nodes (24): api, boundedRequest(), request(), App(), IDENTITIES, NAV, OP_LABELS, AiBrainInspector() (+16 more)

### Community 4 - "Agent Registry & KB Search Concepts"
Cohesion: 0.08
Nodes (40): ai_brain.agent_registry, billing_agent, kb_articles hybrid search, logistics_agent, loyalty_accounts collection, loyalty_agent, order_agent, product_agent (+32 more)

### Community 5 - "Guardrails (Two-Band)"
Cohesion: 0.09
Nodes (34): check_input(), check_output(), GuardrailResult, _is_pii_only(), _load_denylist_and_policy(), log_event(), needs_security_review(), overlap_score() (+26 more)

### Community 6 - "Product Search & Budget Pre-filter"
Cohesion: 0.10
Nodes (33): build_product_pipeline(), detect_category(), _local_rank(), parse_price_ceiling(), Relevância pesa mais, mas nota e disponibilidade desempatam — igual a um…, Singular/plural aproximado em pt-BR: 'fones' e 'fone' precisam casar na busca…, Extrai teto de preço tanto em dígitos (R$ 350) quanto por extenso (até mil…, Busca de catálogo no Atlas. O teto de preço entra no `filter` do $vectorSearch… (+25 more)

### Community 7 - "Settings & Config"
Cohesion: 0.14
Nodes (26): field_validator, Configuração central; segredos vêm somente do ambiente., Settings, DataStore, Uma porta pequena para Atlas com fallback determinístico para testes locais., Schema-at-boundary: cada handoff/trace é validado pelo próprio MongoDB, não só…, list_reviews(), override_rate() (+18 more)

### Community 8 - "Scope Integration Tests"
Cohesion: 0.13
Nodes (31): LLMGateway, O veredito de escopo (embedding) decide ANTES de gastar LLM; a faixa ambígua…, Responde ao classificador de segurança e ao de roteamento conforme o teste…, RoutingLLM, test_a_crashing_classifier_never_drops_the_turn(), test_a_generic_recommend_verb_alone_can_be_refused_by_a_decisive_out_verdict(), test_a_routed_message_that_targets_a_third_party_still_reaches_the_security_classifier(), test_a_strong_keyword_never_pays_for_the_scope_classifier() (+23 more)

### Community 9 - "Turn Classifier & Probes"
Cohesion: 0.10
Nodes (24): classify(), _overlap(), Classificador "este turno depende da memória DESTE cliente?" — feito no…, Devolve {personal, score, threshold, nearest, method, error, latency_ms}.…, _threshold(), create_index(), main(), Semeia SÓ o classificador de turno pessoal (probes + índice vetorial) —… (+16 more)

### Community 10 - "Agent Runners"
Cohesion: 0.17
Nodes (28): AgentResult, extract_id(), _is_trivial_lookup(), llm_synthesize(), Any, Deixa o modelo redigir a resposta em cima do dado JÁ retornado do Mongo — a…, Devolve (artigos, estratégia). A estratégia vira o título do evento de timeline…, Modo econômico: pula a chamada real ao Anthropic quando a mensagem é só o… (+20 more)

### Community 11 - "Greeting & Capability Detection"
Cohesion: 0.14
Nodes (22): is_capabilities_question(), is_greeting(), Minúsculas, sem acento, pontuação virando espaço: "Bom dia, tudo bem?" → "bom…, Cumprimento/abertura de conversa — curto e sem pedido embutido., O que você faz?" é pergunta sobre o atendimento, não assunto alheio: responde…, _words(), CountingLLM, LLMGateway (+14 more)

### Community 12 - "ADR Set 001-004 (PT)"
Cohesion: 0.10
Nodes (25): ADR-001 coordenacao orientada a documentos, ADR-002 memoria por LLM e turno pessoal, ADR-003 guardrail em duas faixas e fora de escopo, ADR-004 escopo por embedding e medicao, Agents are data, not deploys, Agents table, docs/architecture.md, billing_agent (+17 more)

### Community 13 - "Decisions & Audit"
Cohesion: 0.17
Nodes (22): build_audit_event(), build_decision_doc(), decision_trail(), new_decision_id(), Any, Spine de decisão e auditoria — o registro imutável do que o sistema decidiu, e…, Grava a decisão e, junto, o evento de auditoria correspondente. Os dois inserts…, Trilha completa de um cliente (ou de um pedido): decisões + eventos, mais… (+14 more)

### Community 14 - "Policies & Safe Filters"
Cohesion: 0.18
Nodes (22): guarded_order_update(), GuardedStatusError, public_document(), Any, Reconstrói o filtro inteiro; nenhuma opção fornecida pelo modelo sobrevive., Tentativa de escrever, pelo caminho genérico, um status que exige regra de…, Caminho genérico de escrita de status. Reconstrói filtro e update no servidor., Escrita de um status guardado. **Uso exclusivo de `app.replacement`** — é ela… (+14 more)

### Community 15 - "Auto-Warmup Service"
Cohesion: 0.16
Nodes (13): Warmup automático do cache semântico: a demo abre e o cache já está quente.…, Dispara em segundo plano e devolve o estado atual na hora (a UI não espera o…, WarmupService, FakeOrchestrator, Warmup automático: aquece perguntas GENÉRICAS por área (as únicas que o cache…, service(), test_a_failed_run_can_be_retried_immediately(), test_concurrent_triggers_share_one_run() (+5 more)

### Community 16 - "UI Screens & Design"
Cohesion: 0.10
Nodes (24): Agent Control Plane app shell (nav Chat/Agentes/Guardrails/Metricas, identity picker, live + Atlas status pills), Inspector list of the 8 seeded agents on claude-haiku-4-5, Design decision: empty state pre-announces the coordination view instead of hiding it, KPI strip: agentes ativos, handoffs no turno, origem da rota, tokens estimados, Chat Home Screenshot (empty state), Three-pane turn layout: Canal do Cliente / Raio-X do Turno / Inspetor MongoDB, 'Agentes em acao' chain strip: Suporte to Produtos to Pedidos to Logistica to Pedidos, Rationale: capture from page top so chain strip and collections row both appear, after a real 5-hop run (+16 more)

### Community 17 - "Guidance & Welcome Replies"
Cohesion: 0.11
Nodes (22): blocked_reply(), build_suggestions(), greeting_reply(), _in_transit(), is_meta_question(), is_thanks(), looks_like_own_pii(), meta_reply() (+14 more)

### Community 18 - "Calibration Tests"
Cohesion: 0.10
Nodes (7): Calibração medida: escolha do limiar com erros, seleção de alvos (--only) e…, Categoria nova no conjunto de situações que o calibrador não conhece não entra…, aggregate() devolve o score que o teste atribuiu ao texto consultado., ScoredAtlas, test_every_scope_relevant_category_of_the_dataset_is_mapped_to_a_label(), test_overlap_is_not_written_without_allow_errors_but_is_with_it(), test_perfect_separation_suggests_midpoint_and_measures_the_brain_collection()

### Community 19 - "Replacement Chain"
Cohesion: 0.15
Nodes (18): order_replacement_chain(), Cadeia de trocas do pedido, via $graphLookup no Atlas (loop em Python só em…, apply_replacement(), assess_replacement(), block_for_quality_review(), _chain_event(), Any, Troca de produto como operação de domínio — o único caminho que efetiva… (+10 more)

### Community 20 - "LLM Gateway"
Cohesion: 0.17
Nodes (14): LLMGateway, Explicit per-model protocol routing through Grove, with a per-endpoint breaker., parametrize, A API rejeita bloco de texto vazio (BadRequestError). Contexto dinâmico vazio é…, Classificação precisa ser determinística (temperature 0). Nem todo modelo…, test_cache_hit_preserves_replay_but_does_not_count_old_operations(), test_empty_dynamic_context_never_sends_an_empty_system_block(), test_fallback_records_each_attempt_without_exposing_prompts() (+6 more)

### Community 21 - "Orchestration Service"
Cohesion: 0.18
Nodes (13): _next_steps(), OrchestrationService, DataStore, LLMGateway, Uma linha: a chave do agente, `conversa` ou `nenhum`. Classificar é decisão,…, Pattern Parallel Fan-Out/Synthesis: agentes independentes rodam ao mesmo tempo…, Aplica só o DELTA deste turno via `update_one` atômico — nunca reescreve o…, Contador cumulativo de toque por collection+operação — alimenta o painel… (+5 more)

### Community 22 - "Situations Eval & Generator Concepts"
Cohesion: 0.12
Nodes (20): eval_situations.py, generate_situations.py (--append), situations.json (287 cases / 39 categories), Boundary label `handled`, eval_situations.py, generate_situations.py (--append), situations.json (287 cases / 39 categories), Situation verifier (+12 more)

### Community 23 - "Agent Memory Concepts"
Cohesion: 0.13
Nodes (20): Design: dark hero + JSON code card, three-column body, numbered benefit strip, Long-term Memory (episodic, semantic, procedural), Claim: Agent Memory e uma hierarquia de memorias, nao uma collection unica, Memory Engineering Stack (document model, automated embedding, Vector Search, Search+RRF, TTL, Change Streams), recall(): working -> cache -> long_term, vector + lexical + tenant filters, Shared Memory — camada transversal (ai_brain + multi_agent_poc), Short-term Memory (working memory + semantic cache), Slide: Uma plataforma de memoria — Agent Memory (template MongoDB) (+12 more)

### Community 24 - "Runtime Config"
Cohesion: 0.17
Nodes (15): get_settings(), main(), Sincroniza SÓ os roteiros de demo (brain.demo_scenarios) com app/seed_data.py —…, sync(), agent_doc(), extract(), live(), fixture (+7 more)

### Community 25 - "API Routes (main.py)"
Cohesion: 0.18
Nodes (18): decisions(), eval_runs(), get_metrics(), guardrails(), handoffs(), health(), inspector(), latest_conversation() (+10 more)

### Community 26 - "Resilience E2E Tests"
Cohesion: 0.22
Nodes (16): fact(), facts_of(), LLMGateway, parametrize, Ataques fim-a-fim (orquestrador real, DEMO_MODE, LLM roteirizado): memória…, Só o extrator responde (JSON roteirizado); demais agentes caem no template…, ScriptedLLM, test_episode_memory_cannot_carry_user_text_into_prompts() (+8 more)

### Community 27 - "Frontend Dependencies"
Cohesion: 0.11
Nodes (18): dependencies, react, react-dom, vite, @vitejs/plugin-react, devDependencies, name, private (+10 more)

### Community 28 - "Threshold Calibration"
Cohesion: 0.20
Nodes (17): ArgumentParser, apply_turn_threshold(), best_with_errors(), block_threshold_from(), build_parser(), calibrate(), denylist_filters(), main() (+9 more)

### Community 29 - "Route Handlers"
Cohesion: 0.16
Nodes (18): agents(), approve_candidate(), chat(), create_token(), demo_reset(), demo_scenarios(), events_stream(), Aquece o cache em segundo plano e responde na hora. Aberto de propósito (a UI… (+10 more)

### Community 30 - "Orchestration & Scope Gate"
Cohesion: 0.20
Nodes (15): A mensagem chega ao classificador de escopo? Só quando NADA mais decidiu: sem…, reaches_scope_classifier(), cheap_route(), detect_fanout(), deterministic_orchestrator(), has_catalog_anchor(), _padded(), Texto sem acento e sem pontuação, com espaço nas bordas: permite casar palavra… (+7 more)

### Community 31 - "Calibration & Scope Config Concepts"
Cohesion: 0.16
Nodes (17): calibrate_thresholds.py, LLM security classifier + self-reinforcing write-back, scope_classifier_config, seed_turn_probes.py, turn_classifier (threshold 0.7162), vector_block_threshold = 0.8814, vector_threshold, calibrate_thresholds.py (+9 more)

### Community 32 - "DataStore Internals"
Cohesion: 0.22
Nodes (5): _driver_session(), _matches(), Desembrulha o handle para o que o pymongo espera receber em `session=`., Só para pipelines reais ($vectorSearch/$unionWith) — sem equivalente em…, Live feed de handoffs do cliente: Change Stream no Atlas, poll no modo…

### Community 33 - "Scope Classifier Concepts"
Cohesion: 0.16
Nodes (16): reaches_scope_classifier, scope_classifier.py (in/out/chat), scope_probes collection (214), scope_probes_vs index, seed_scope_probes.py, Out-of-scope handling (0 tokens), reaches_scope_classifier, ROUTER_PROMPT (+8 more)

### Community 34 - "ADR-003/004 Security Concepts"
Cohesion: 0.17
Nodes (15): ADR-003 two-band guardrail and out-of-scope, ADR-004 scope by embedding + situations, guardrails.needs_security_review, ADR-003 two-band guardrail and out-of-scope, ADR-004 scope by embedding + situations, guardrails.needs_security_review, Routing LLM before security in ambiguous band, Security model (customer_key from JWT) (+7 more)

### Community 35 - "Token Budget"
Cohesion: 0.20
Nodes (8): BudgetExceeded, Troca a estimativa heurística (chars/4) pelo uso REAL reportado pela API.…, TurnBudget, SlidingWindowLimiter, test_agent_budget_blocks_single_agent(), test_budget_isolated_per_agent_and_global(), test_sliding_window_prunes_old_entries(), RuntimeError

### Community 36 - "Models & Requests"
Cohesion: 0.19
Nodes (13): update_agent(), AgentUpdate, ChatRequest, ChatResponse, OrderStatusUpdate, field_validator, Próximo passo clicável, sempre derivado de um documento que existe., Resolução de um caso escalado. `decision` é fechada: o analista escolhe entre… (+5 more)

### Community 37 - "Scope Classifier Tests"
Cohesion: 0.19
Nodes (10): Atlas, parametrize, Classificador de escopo por embedding (in / out / chat): margem entre líder e…, where is my order?": os 12 vizinhos são todos `in`. `out` ausente = mais…, rows(), test_a_label_missing_among_the_neighbours_is_bounded_by_the_last_neighbour_not_treated_as_zero(), test_leader_must_beat_the_runner_up_by_its_own_margin(), test_query_uses_the_scope_index_in_the_brain_db_with_a_neighbourhood() (+2 more)

### Community 38 - "Agent Registry & Fan-out"
Cohesion: 0.18
Nodes (15): agent_registry, billing_agent, Parallel fan-out, Handoff loop MAX_HOPS=5, LLM never chooses what to fetch, logistics_agent, loyalty_agent, MongoDB as coordination plane (+7 more)

### Community 39 - "Handoff & Routing Concepts"
Cohesion: 0.15
Nodes (14): agent_handoffs / agent_traces, cheap_route (router.py), orchestrator, Pendencias conhecidas, ROUTER_PROMPT, has_catalog_anchor + weak_product_route gate, agent_handoffs / agent_traces, cheap_route (router.py) (+6 more)

### Community 40 - "DataStore & Transactions"
Cohesion: 0.15
Nodes (11): as_aware(), _compare(), is_transient_transaction_error(), Escrita de negócio e registro de decisão como uma coisa só. O problema que isto…, Documento antigo/legado pode trazer datetime naive; trata como UTC (é assim que…, Como o Mongo: campo ausente/de outro tipo não casa em comparação (em vez de…, Handle de uma transação em curso. `driver_session` é a sessão do pymongo, ou…, True quando o MongoDB pede explicitamente para repetir a operação. Duas… (+3 more)

### Community 41 - "Scope Classifier (Embedding)"
Cohesion: 0.21
Nodes (13): best_scores(), classify(), decide(), DataStore, Classificador de ESCOPO — "esta mensagem é assunto da loja?" — feito no…, Regra pura (testável sem Atlas). Devolve (escopo, margem do líder sobre o…, Melhor score por rótulo entre os vizinhos, ou None se não deu para consultar…, Devolve {scope: in|out|chat|unsure, margin, in_score, out_score, chat_score,… (+5 more)

### Community 42 - "Replacement Chain Tests"
Cohesion: 0.18
Nodes (5): _store_com_pedidos(), test_order_agent_bloqueia_a_troca_quando_a_cadeia_e_recorrente(), test_order_agent_troca_normalmente_quando_nao_ha_defeito_recorrente(), test_travessia_indisponivel_degrada_em_vez_de_quebrar_o_turno(), DataStore

### Community 43 - "Langfuse Tracing"
Cohesion: 0.18
Nodes (13): ADR-001 multi-agent architecture, ADR-002 LLM memory and personal turn, looks_like_instruction filter, LLM memory extractor (memory.py), ADR-001 multi-agent architecture, ADR-002 LLM memory and personal turn, Long-term memory episodes, looks_like_instruction filter (+5 more)

### Community 44 - "ADR Set 001-004 (EN)"
Cohesion: 0.19
Nodes (7): Any, build_turn_trace(), get_langfuse(), _NoopLangfuse, _NoopTrace, Sem chave configurada (ou Langfuse fora do ar): instrumentação vira no-op,…, Uma trace por turno cobrindo a timeline INTEIRA — roteamento, decisão de cache,…

### Community 45 - "Budget & Cascade Concepts"
Cohesion: 0.22
Nodes (9): _cascade_lookup_fallback(), _cascade_lookup_raw(), cascade_store_short_term(), CascadeResult, DEMO_MODE não tem índice de vetor real — sem embedding local pra simular cosine…, Registra o turno APENAS na memória de curto prazo. Existe para o caminho de…, UMA consulta decide HIT/MISS antes do LLM: $vectorSearch em curto_prazo…, API da PoV multi-agente. (+1 more)

### Community 46 - "Security & Auth"
Cohesion: 0.18
Nodes (11): get_store(), current_customer(), issue_token(), Depends, Request, request_identity_key(), require_admin(), secrets_equal() (+3 more)

### Community 47 - "Out-of-Scope Replies (Word List)"
Cohesion: 0.21
Nodes (12): out_of_scope_reply(), Mensagem fora do domínio de atendimento — o caso 'pergunta sem sentido'. Não…, has_domain_signal(), has_weak_signal(), out_of_scope_sentences(), True quando a mensagem tem sinal FORTE de que fala com esta loja., Só palavras genéricas (ajuda, conta, valor...) — inconclusivo sem o…, Numa mensagem MISTA (várias frases, ao menos uma da loja), as frases sem nenhum… (+4 more)

### Community 48 - "Seed Data & Demo Scenarios"
Cohesion: 0.26
Nodes (9): seed_documents(), main(), Restaura os saldos que a própria demo/eval consome (idempotente, só as contas…, restore(), create_search_indexes(), main(), Seed idempotente do plano de dados e do plano de coordenação., seed() (+1 more)

### Community 49 - "Legacy Memory Migration"
Cohesion: 0.32
Nodes (11): clear_legacy_price_cap(), main(), migrate(), Migra documentos legados de `customer_memory` (fact_type/value) para o formato…, Devolve quantos documentos legados foram (ou seriam) migrados., Remove o teto de R$ 350 que a migração anterior pôs nos fatos price_sensitive…, legacy_store(), test_apply_is_idempotent() (+3 more)

### Community 50 - "Calibrator Bug & Dataset Growth"
Cohesion: 0.17
Nodes (13): Calibrator category-mapping bug, Set growth to 287, calibrate_thresholds.py --only scope, generate_situations.py (--append), Precision-first thresholds, floor 0.04, Async reindex on adding probes, Outlier 'o roteador que adquiri nao conecta', Small samples (+5 more)

### Community 51 - "ADR Set (Mirror)"
Cohesion: 0.18
Nodes (13): ADR-001 Coordenacao multi-agente orientada a documentos, ADR-002 Memoria LLM e turno pessoal, ADR-003 Guardrail em duas faixas, ADR-004 Escopo por embedding e medicao, agent_conversations, ai_brain.agent_registry, Parallel fan-out order + billing, agent_handoffs / agent_traces (+5 more)

### Community 52 - "Long-Term Context"
Cohesion: 0.32
Nodes (11): cascade_long_term_context(), MISS nos dois: puxa contexto de longo prazo (memória episódica do cliente) pro…, utcnow(), Cache útil E seguro: memória estruturada do cliente não bloqueia pergunta…, O cache global guarda a resposta SEM orçamento; servi-la a quem tem teto…, test_customer_with_budget_never_receives_the_generic_cached_recommendation(), test_generic_answer_is_cached_even_for_customer_with_facts_and_history(), test_global_cache_serves_other_customers_the_generic_answer() (+3 more)

### Community 53 - "Cost Economics"
Cohesion: 0.24
Nodes (8): Estimated LLM cost from provider usage; absent tariffs are never zero cost., summarize_evals(), grade_case(), grade_outcome(), main(), Eval harness: roda o golden dataset (app/seed_data.py:EVAL_CASES) contra o…, run(), snapshot()

### Community 54 - "Hybrid KB Retrieval (RRF)"
Cohesion: 0.26
Nodes (10): build_kb_lexical_pipeline(), build_kb_rank_fusion_pipeline(), build_kb_vector_pipeline(), Combina rankings lexical e vetorial sem comparar escalas de score. Continua…, Perna semântica: Atlas Vector Search com Automated Embedding (voyage-4)., Perna lexical: BM25 com boost no título (analyzer português)., Híbrido server-side: $rankFusion funde as duas pernas dentro do banco (MongoDB…, reciprocal_rank_fusion() (+2 more)

### Community 55 - "App Lifespan"
Cohesion: 0.18
Nodes (11): set_store(), budget_handler(), lifespan(), log(), request_context(), unhandled_error_handler(), BudgetExceeded, Exception (+3 more)

### Community 56 - "LLM Circuit Breaker"
Cohesion: 0.18
Nodes (4): _CircuitBreaker, TurnBudget, False quando o circuito está aberto e ainda dentro da janela de curto-circuito., _validate_grove_url()

### Community 57 - "Live Event Stream (SSE)"
Cohesion: 0.29
Nodes (7): handoff_event_stream(), Adapt the Change Stream to SSE with immediate confirmation and heartbeats., ConnectedRequest, IdleStore, OneHandoffStore, test_sse_confirms_connection_before_first_handoff_and_then_emits_data(), test_sse_sends_heartbeat_while_change_stream_is_idle()

### Community 58 - "Situations Eval Harness"
Cohesion: 0.25
Nodes (9): compare(), main(), outcome_of(), Mede o agente REAL (Atlas + LLM) contra tests/data/situations.json — o que um…, O que o cliente viu: bloqueado, orientação de escopo, boas-vindas ou qual…, Taxas que importam ao cliente, separadas de acerto de rótulo., report(), run() (+1 more)

### Community 59 - "ADR-004 Baseline & Decisions"
Cohesion: 0.22
Nodes (11): ADR-002 LLM memory and personal turn, ADR-003 two-band guardrail, Baseline before ADR-004 (n=229), ADR-004 decision (scope by embedding), router.DOMAIN_VOCAB word list (ADR-003), Margin-based decision rule, Missing-label bounded by last neighbour, No-verdict fallback to word list (+3 more)

### Community 60 - "Cache & Routing Principles"
Cohesion: 0.20
Nodes (11): Semantic cache cascade, cheap_route, Deterministic routing is the rule, Fail closed only where risk, Input guardrail layers, Output guardrail, Routing step, short_term_memory (+3 more)

### Community 61 - "LLM Cost Models"
Cohesion: 0.20
Nodes (11): Claude Haiku 4.5 (Anthropic) - $1.41, 25.2% of cost, Claude Opus 4.8 (Anthropic) - $0.18, 3.2% of cost, Claude Opus 5 (Anthropic) - $0.0015, 0.0% of cost, Claude Sonnet 4.5 (Anthropic) - $1.24, 22.2% of cost, Claude Sonnet 4.6 (Anthropic) - $2.09, 37.3% of cost, Claude Sonnet 5 (Anthropic) - $0.65, 11.7% of cost, GitHub Copilot (usage source), GPT-5.3 Codex (OpenAI) - $0.02, 0.4% of cost (+3 more)

### Community 62 - "LIVE Suites & Pre-push"
Cohesion: 0.33
Nodes (9): LIVE test suites, pre-push hook (.githooks), DEMO_MODE hides driver bugs, LIVE test suites, pre-push hook (.githooks), tests/test_live*.py, pre-push hook, LIVE suites (+1 more)

### Community 63 - "Concurrency Tests"
Cohesion: 0.22
Nodes (8): Regressão do lost update: dois turnos concorrentes na MESMA conversation_id…, $set só deve mencionar active_order_id/active_invoice_id quando o turno de fato…, Regressão da falta de idempotência: dois resgates idênticos disparados quase…, Um segundo resgate idêntico, chegando DEPOIS do primeiro já ter terminado (não…, test_loyalty_redemption_is_idempotent_under_concurrent_retry(), test_loyalty_redemption_retry_returns_previous_result_without_double_debit(), test_two_concurrent_turns_on_the_same_conversation_do_not_lose_a_turn(), test_update_conversation_preserves_active_order_id_when_turn_does_not_touch_it()

### Community 64 - "LIVE Random Tests"
Cohesion: 0.22
Nodes (3): live(), fixture, Bateria LIVE de perguntas ALEATÓRIAS (Atlas + LLM reais): cd backend && LIVE=1…

### Community 65 - "Replacement Chain (graph.py)"
Cohesion: 0.25
Nodes (7): build_order_chain_pipeline(), Travessia de grafo sobre `orders`: cadeia de trocas de um pedido. Um pedido…, Segue replacement_order_id -> order_id a partir de um pedido, até `max_depth`…, Traduz a cadeia crua em sinais de negócio. Sem LLM: é aritmética sobre o array., Mesma travessia em Python, para DEMO_MODE/CI — é literalmente o loop que o…, summarize_order_chain(), traverse_order_chain_in_memory()

### Community 66 - "Architecture Components"
Cohesion: 0.25
Nodes (8): Main components table, decisions.py / reviews.py, graph.py $graphLookup over orders, langfuse_client.py, Persistence step, scope_classifier.py, Scope step (ADR-004), Security and isolation

### Community 67 - "Misc 67"
Cohesion: 0.48
Nodes (6): Fail startup on configurations that would expose demo credentials., validate_runtime_security(), production_settings(), parametrize, test_insecure_production_configuration_is_rejected(), test_secure_production_configuration_is_accepted()

### Community 69 - "Misc 69"
Cohesion: 0.48
Nodes (6): generate(), main(), Gera o conjunto de SITUAÇÕES (tests/data/situations.json) para medir o agente…, split_of(), verify(), TurnBudget

### Community 70 - "Misc 70"
Cohesion: 0.48
Nodes (6): create_index(), main(), DataStore, Semeia SÓ o classificador de escopo (probes rotulados in/out/chat + índice…, Upsert dos probes em <brain_db>.scope_probes. Devolve quantos são novos., seed_probes()

### Community 71 - "Misc 71"
Cohesion: 0.29
Nodes (7): ADR-002 Memória por LLM e turno pessoal, Budget pre-filter (max_price_brl in $vectorSearch), Long-term episode memory (system labels only), looks_like_instruction, LLM memory extractor with supersession, Personal-turn gates and turn classifier, Semantic cache cascade (short-term/session/customer/global)

### Community 72 - "Misc 72"
Cohesion: 0.29
Nodes (7): claude-haiku-4-5 model, eval.py avaliador, eval_runs collection, gpt-5.6-luna model, grove-mixed-live eval run, bruno-paraphrase-exfiltration eval case, ana-paraphrase-jailbreak eval case

### Community 73 - "Misc 73"
Cohesion: 0.29
Nodes (7): DEMO_MODE DataStore, Known gaps, No LangGraph in code (scope.md mismatch), No graph framework, Stack, Two logical DBs, Architecture overview

### Community 74 - "Misc 74"
Cohesion: 0.33
Nodes (6): DEMO_MODE in-memory DataStore, denylist_autoembed_v1 semantic denylist, GROUNDING_RULES, llm_synthesize grounded responses, overlap_score (Jaccard), Static denylist + near-miss

### Community 75 - "Misc 75"
Cohesion: 0.47
Nodes (5): check(), main(), Client, Smoke test contra a API no ar. Uso: python tests/smoke.py [URL]., token()

### Community 76 - "Misc 76"
Cohesion: 0.33
Nodes (5): Architecture, Commands, Continuidade da revisão de resiliência, Known gaps (verified against code, not just docs), Project

### Community 77 - "Misc 77"
Cohesion: 0.33
Nodes (6): DEMO_MODE in-memory DataStore, denylist_autoembed_v1 semantic denylist, GROUNDING_RULES, llm_synthesize grounded responses, overlap_score (Jaccard), Static denylist + near-miss

### Community 78 - "Misc 78"
Cohesion: 0.40
Nodes (6): Grove Gateway, llm_calls ledger, LLM_PRICES config, Fórmula de custo por chamada (tarifas separadas), Fórmula de estimativa por média histórica, Grove Gateway captured costs table

### Community 79 - "Misc 79"
Cohesion: 0.33
Nodes (6): CI, DEMO_MODE=1 without Atlas, How to run (start.sh), Production boundary, Smoke cache validation, Tests

### Community 80 - "Misc 80"
Cohesion: 0.40
Nodes (4): Architecture, Commands, Known gaps (verified against code, not just docs), Project

### Community 81 - "Misc 81"
Cohesion: 0.50
Nodes (4): _jsonable(), Any, Tipos do driver (ObjectId, Decimal128, bytes) viram texto: documentos reais do…, field_serializer

### Community 82 - "Misc 82"
Cohesion: 0.40
Nodes (5): ADR-002 Memoria LLM e turno pessoal, ADR-003 Guardrail em duas faixas e fora de escopo, ADR-003 discarded alternatives, Domain vocabulary (DOMAIN_VOCAB / has_domain_signal), Out-of-scope handling (deterministic)

### Community 83 - "Misc 83"
Cohesion: 0.40
Nodes (4): MDB_MCP_CONNECTION_STRING, npx, mongodb, mongodb-mcp-server

### Community 84 - "Misc 84"
Cohesion: 0.50
Nodes (3): ADR-001-arquitetura-multi-agente.md, Documentação dividida por leitor, Documentação faltante (RUNBOOK, data-model, ADR-002+, SECURITY.md)

### Community 85 - "Misc 85"
Cohesion: 0.67
Nodes (4): Claude Haiku 4.5 (Anthropic) usage row, GPT-5.6 Luna (OpenAI) usage row, Usage by Model cost table (Grove gateway dashboard), Grove gateway (Anthropic APIM) — PoV LLM access layer

### Community 87 - "Misc 87"
Cohesion: 0.67
Nodes (3): Known gaps, Langfuse build_turn_trace, SSE + Change Stream + op counters

### Community 89 - "Misc 89"
Cohesion: 0.67
Nodes (3): Known gaps, Langfuse build_turn_trace, SSE + Change Stream + op counters

### Community 90 - "Misc 90"
Cohesion: 0.67
Nodes (3): LLM_BLENDED_PRICES config, Premissa histórica 18/09/2026 (substituída), Regra vigente 19/09/2026 (LLM_BLENDED_PRICES)

### Community 92 - "Misc 92"
Cohesion: 0.67
Nodes (3): Backend tests and lint job, CI Workflow, Frontend build job

## Ambiguous Edges - Review These
- `MODO ADMIN toggle gating per-agent enable/disable switches` → `Principle: input validated once per turn, before any model, memory or trace`  [AMBIGUOUS]
  docs/screenshots/04-agents-registry.png · relation: conceptually_related_to
- `GPT-5.3 Codex (OpenAI) - $0.02, 0.4% of cost` → `Grove Gateway (usage source)`  [AMBIGUOUS]
  docs/internal/assets/grove-costs-2026-09-18.png · relation: shares_data_with

## Knowledge Gaps
- **182 isolated node(s):** `devDependencies`, `name`, `private`, `build`, `dev` (+177 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 560 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **38 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `MODO ADMIN toggle gating per-agent enable/disable switches` and `Principle: input validated once per turn, before any model, memory or trace`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `GPT-5.3 Codex (OpenAI) - $0.02, 0.4% of cost` and `Grove Gateway (usage source)`?**
  _Edge tagged AMBIGUOUS (relation: shares_data_with) - confidence is low._
- **Why does `DataStore` connect `Settings & Config` to `Demo Reset & Episodic Memory`, `Semantic Cache Cascade`, `Guardrails (Two-Band)`, `Product Search & Budget Pre-filter`, `Turn Classifier & Probes`, `Agent Runners`, `Greeting & Capability Detection`, `Decisions & Audit`, `Auto-Warmup Service`, `Guidance & Welcome Replies`, `Replacement Chain`, `Runtime Config`, `API Routes (main.py)`, `Resilience E2E Tests`, `Route Handlers`, `DataStore Internals`, `Models & Requests`, `DataStore & Transactions`, `Budget & Cascade Concepts`, `Security & Auth`, `Seed Data & Demo Scenarios`, `Legacy Memory Migration`, `Long-Term Context`, `App Lifespan`, `Live Event Stream (SSE)`, `Concurrency Tests`, `LIVE Random Tests`?**
  _High betweenness centrality (0.117) - this node is a cross-community bridge._
- **Why does `Settings` connect `Settings & Config` to `Demo Reset & Episodic Memory`, `Semantic Cache Cascade`, `Guardrails (Two-Band)`, `Product Search & Budget Pre-filter`, `Turn Classifier & Probes`, `Greeting & Capability Detection`, `Decisions & Audit`, `Auto-Warmup Service`, `Runtime Config`, `Resilience E2E Tests`, `DataStore & Transactions`, `ADR Set 001-004 (EN)`, `Security & Auth`, `Seed Data & Demo Scenarios`, `Legacy Memory Migration`, `Long-Term Context`, `Cost Economics`, `Concurrency Tests`, `Misc 67`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `scope_classifier.py (in/out/chat)` connect `Scope Classifier Concepts` to `Architecture Components`, `ADR-003/004 Security Concepts`, `Handoff & Routing Concepts`, `ADR-004 Baseline & Decisions`, `Calibration & Scope Config Concepts`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Are the 64 inferred relationships involving `DataStore` (e.g. with `order_replacement_chain()` and `run_billing_agent()`) actually correct?**
  _`DataStore` has 64 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `Settings` (e.g. with `DataStore` and `build_turn_trace()`) actually correct?**
  _`Settings` has 7 INFERRED edges - model-reasoned connections that need verification._