# Graph Report - multiagente-atendimento  (2026-09-22)

## Corpus Check
- 7 files · ~201,359 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1685 nodes · 3390 edges · 150 communities (87 shown, 61 thin omitted)
- Extraction: 94% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 186 edges (avg confidence: 0.89)
- Token cost: 56,000 input · 24,000 output

## Community Hubs (Navigation)
- Memória do cliente (LLM)
- Agentes especializados
- Documento de arquitetura
- README
- Frontend da demo
- Bateria de caos
- Classificador de turno pessoal
- Guardrail de entrada e saída
- Calibração medida de limiares
- Turno pessoal fora do cache
- Escopo integrado ao turno
- Escopo por embedding
- Isolamento de banco de teste
- Test Live Random
- Orquestração do turno
- Troca de produto
- Fila de revisão humana
- Políticas de escrita segura
- Warmup do cache
- 01 Chat Home
- Orçamento de tokens do turno
- Configuração e segredos
- Respostas de orientação
- Economia do gateway de LLM
- Cadeia de trocas ($graphLookup)
- Resiliência do supervisor
- Consultas MongoDB do briefing
- DataStore e fronteira de tools
- API FastAPI
- Pov Agent Memory Mongodb Template
- Test Live Scenarios
- Ataques fim-a-fim
- Dependências do frontend
- Trilha de decisões
- Trace do turno (Langfuse)
- Fora de escopo e saudação
- Crash-resume com SIGKILL
- Eval de roteamento
- Regressão de caos
- Mapa de agentes
- Injeção de falha
- Contratos de resposta
- JWT e mascaramento
- Roteamento determinístico
- Roteamento determinístico (2)
- Adr 001 Arquitetura Multi Agente
- Mapa de agentes (2)
- Tracing por span
- Busca híbrida e vetorial
- Adr 004 Escopo Por Embedding E Medicao P
- Adr 004 Escopo Por Embedding E Medicao P (2)
- Test Cache Eligibility
- API FastAPI (2)
- Test Live Stream
- Eval por situações
- Grove Costs 2026 09 18
- Adr 004 Escopo Por Embedding E Medicao P (3)
- Guardrails de borda
- Comportamento dos agentes (briefing)
- Mapa de agentes (3)
- Gateway de LLM
- API FastAPI (3)
- Resiliência do supervisor (2)
- Respostas de orientação (2)
- Golden eval (caixa-preta)
- Adr 004 Escopo Por Embedding E Medicao P (4)
- API FastAPI (4)
- Test Security Config
- Adr 002 Memoria Llm E Turno Pessoal
- Agent Quality Economics
- Mapa de agentes (4)
- Mapa de agentes (5)
- Métricas em processo
- Smoke caixa-preta
- Guia do repositório
- Agent Quality Economics (2)
- Baseline de testes
- Mapa de agentes (6)
- DataStore e fronteira de tools (2)
- DataStore e fronteira de tools (3)
- Custo por chamada
- Adr 003 Guardrail Em Duas Faixas
- Mcp
- Resiliência do supervisor (3)
- Slide Docs Brief
- Grove Costs 2026 09 19
- Http Deadline Test
- Escopo do PoV
- Mapa de agentes (7)
- Gateway de LLM (2)
- Consulta de spans
- Warmup do cache (2)
- Grove Cost Guide
- Ci
- Mapa de agentes (8)
- Mapa de agentes (9)
- Documento de arquitetura (2)
- Comportamento dos agentes (briefing) (2)
- Comportamento dos agentes (briefing) (3)
- Documento de arquitetura (3)
- Ui Flows
- Grove Cost Guide (2)
- Index
- Pre Push
- Implementation Plan
- Start
- Mapa de agentes (10)
- Mapa de agentes (11)
- Mapa de agentes (12)
- Mapa de agentes (13)
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Requirements
- Requirements (2)
- Requirements (3)
- Requirements (4)
- Community 125
- Community 126
- Community 127
- Community 128
- Adr 003 Guardrail Em Duas Faixas (2)
- Adr 003 Guardrail Em Duas Faixas (3)
- Adr 003 Guardrail Em Duas Faixas (4)
- Adr 003 Guardrail Em Duas Faixas (5)
- Adr 004 Escopo Por Embedding E Medicao P (5)
- Documento de arquitetura (4)
- Documento de arquitetura (5)
- Documento de arquitetura (6)
- Comportamento dos agentes (briefing) (4)
- Comportamento dos agentes (briefing) (5)
- Comportamento dos agentes (briefing) (6)
- Comportamento dos agentes (briefing) (7)
- Comportamento dos agentes (briefing) (8)
- Comportamento dos agentes (briefing) (9)
- Consultas MongoDB do briefing (2)
- Consultas MongoDB do briefing (3)
- Consultas MongoDB do briefing (4)
- Ui Flows (2)
- Ui Flows (3)
- Community 148
- Community 149

## God Nodes (most connected - your core abstractions)
1. `DataStore` - 177 edges
2. `Settings` - 79 edges
3. `utcnow()` - 51 edges
4. `OrchestrationService` - 41 edges
5. `cascade_lookup()` - 33 edges
6. `TimelineEvent` - 28 edges
7. `get_settings()` - 28 edges
8. `LLMGateway` - 27 edges
9. `active_budget()` - 25 edges
10. `world()` - 25 edges

## Surprising Connections (you probably didn't know these)
- `summary.embedding_classifiers / embedding_path_live` --semantically_similar_to--> `Limitações conhecidas (sem streaming, concorrência não é carga)`  [INFERRED] [semantically similar]
  eval/FORMAT.md → docs/chaos-report.md
- `synthetic/limitation — honestidade do dataset` --semantically_similar_to--> `situations.json (287 situações, dev/holdout)`  [INFERRED] [semantically similar]
  eval/FORMAT.md → CLAUDE.md
- `issue_token()` --uses--> `Settings`  [INFERRED]
  backend/app/security.py → backend/app/config.py
- `Slide 1 (deck pov-memoria-multi-agente): mesma arte em 16:10` --semantically_similar_to--> `Slide: Memoria e Coordenacao na PoV Multi-Agente (16:9 wide)`  [INFERRED] [semantically similar]
  docs/decks/pov-memoria-multi-agente/slide-1.png → docs/decks/pov-memoria-multi-agente.png
- `situations.json (287 cases / 39 categories)` --references--> `situations.json (229 -> 287 / 33 -> 39 categories)`  [EXTRACTED]
  AGENTS.md → docs/adr/ADR-004-escopo-por-embedding-e-medicao-por-situacoes.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Grove cost capture -> LLM_BLENDED_PRICES -> eval cost reporting** — docs_internal_grove_cost_guide_regra_vigente_19_09, docs_agent_quality_economics_llm_blended_prices, docs_agent_quality_economics_eval_py, docs_agent_quality_economics_ledger_de_chamadas [EXTRACTED 0.90]
- **Taxonomia de Agent Memory: short-term + long-term + shared coordenados pelo recall()** — docs_decks_pov_agent_memory_mongodb_template_shorttermmemory, docs_decks_pov_agent_memory_mongodb_template_longtermmemory, docs_decks_pov_agent_memory_mongodb_template_sharedmemory, docs_decks_pov_agent_memory_mongodb_template_recallcascade [EXTRACTED 1.00]
- **Scope classification pipeline** — docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_scope_classifier, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_scope_probes, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_scope_probes_vs, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_scope_classifier_config, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_calibrate_thresholds [EXTRACTED 1.00]
- **Situation-based measurement loop** — docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_generate_situations, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_verifier, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_situations, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_dev_holdout_split, docs_adr_adr_004_escopo_por_embedding_e_medicao_por_situacoes_eval_situations [EXTRACTED 1.00]
- **Fluxo de um turno: politica -> recall -> contexto -> handoff -> registro sobre dois planos com TTLs distintos** — docs_decks_pov_memoria_multi_agente_turnmap, docs_decks_pov_memoria_multi_agente_twoplanes, docs_decks_pov_memoria_multi_agente_ttlladder, docs_decks_pov_memoria_multi_agente_orchestratorchains [EXTRACTED 1.00]
- **Shared dark green/monospace design system: nav shell, eyebrow + big claim headline, card grid** — docs_screenshots_01_chat_home_agent_control_plane_shell, docs_screenshots_04_agents_registry_agent_cards, docs_screenshots_05_metrics_kpi_tiles, docs_screenshots_06_guardrails_raw_json_audit [INFERRED 0.85]
- **MongoDB-as-coordination-plane evidence: handoff chain, collection ops, change stream, guardrail audit docs** — docs_screenshots_03_chain_timeline_agents_in_action_strip, docs_screenshots_03_chain_timeline_collections_in_action, docs_screenshots_03_chain_timeline_last_handoff_change_stream, docs_screenshots_05_metrics_collections_table, docs_screenshots_06_guardrails_raw_json_audit [INFERRED 0.85]
- **Five-step README demo narrative: empty chat, chain timeline, registry, metrics, guardrails** — docs_screenshots_01_chat_home_screenshot, docs_screenshots_03_chain_timeline_screenshot, docs_screenshots_04_agents_registry_screenshot, docs_screenshots_05_metrics_screenshot, docs_screenshots_06_guardrails_screenshot [INFERRED 0.95]
- **Resiliência por padrão do supervisor e das tools** — readme_resilience_by_default, readme_supervisor_legacy_500, readme_agent_timeout_seconds, readme_loop_guard_repeats, readme_tool_timeout_seconds, readme_tool_breaker, readme_supervisor [EXTRACTED 1.00]
- **Isolamento de banco para scripts que escrevem dado real** — backend_scripts_isolation, readme_test_databases, readme_allow_demo_db_write, readme_probe_copy_on_read, backend_eval, backend_eval_routing, docs_chaos_report_crash_resume, claude_md_restore_demo_fixtures [EXTRACTED 1.00]
- **O eval prova qual caminho de classificação foi exercitado** — eval_format_embedding_classifiers, claude_md_scope_classifier, claude_md_turn_classifier, readme_probe_copy_on_read, backend_eval_routing [EXTRACTED 1.00]

## Communities (150 total, 61 thin omitted)

### Community 0 - "Memória do cliente (LLM)"
Cohesion: 0.06
Nodes (85): _cascade_lookup_fallback(), _cascade_lookup_raw(), cascade_store_episode(), cascade_store_short_term(), CascadeResult, is_compound_of(), DEMO_MODE não tem índice de vetor real — sem embedding local pra simular cosine…, Registra na memória de longo prazo QUE o cliente tratou de um assunto — não o… (+77 more)

### Community 1 - "Agentes especializados"
Cohesion: 0.07
Nodes (64): AgentResult, build_product_pipeline(), detect_category(), extract_id(), _is_trivial_lookup(), llm_synthesize(), _local_rank(), parse_price_ceiling() (+56 more)

### Community 2 - "Documento de arquitetura"
Cohesion: 0.06
Nodes (46): agent_registry, warmup.py, billing_agent, Semantic cache cascade, cheap_route, Main components table, decisions.py / reviews.py, DEMO_MODE DataStore (+38 more)

### Community 3 - "README"
Cohesion: 0.06
Nodes (45): agent_registry (8 agentes reais, config como dado), Estado que vive só no cluster Atlas, Memória do cliente extraída por LLM e governada pelo servidor, Guardrail vetorial em duas faixas, Trace única por turno no Langfuse, Orquestração e roteamento determinístico, CLAUDE.md — guia do projeto multiagente, restore_demo_fixtures.py (+37 more)

### Community 4 - "Frontend da demo"
Cohesion: 0.06
Nodes (24): api, boundedRequest(), request(), App(), IDENTITIES, NAV, OP_LABELS, AiBrainInspector() (+16 more)

### Community 5 - "Bateria de caos"
Cohesion: 0.09
Nodes (40): circuit_state(), reset_circuits(), _degraded(), env(), _FakeAnthropic, _FakeBlock, _FakeMessages, _FakeResponse (+32 more)

### Community 6 - "Classificador de turno pessoal"
Cohesion: 0.07
Nodes (35): classify(), _overlap(), Classificador "este turno depende da memória DESTE cliente?" — feito no…, Devolve {personal, score, threshold, nearest, method, error, latency_ms}.…, _threshold(), create_index(), main(), Semeia SÓ o classificador de turno pessoal (probes + índice vetorial) —… (+27 more)

### Community 7 - "Guardrail de entrada e saída"
Cohesion: 0.09
Nodes (34): check_input(), check_output(), GuardrailResult, _is_pii_only(), _load_denylist_and_policy(), log_event(), needs_security_review(), overlap_score() (+26 more)

### Community 8 - "Calibração medida de limiares"
Cohesion: 0.07
Nodes (24): ArgumentParser, apply_turn_threshold(), best_with_errors(), block_threshold_from(), build_parser(), calibrate(), denylist_filters(), main() (+16 more)

### Community 9 - "Turno pessoal fora do cache"
Cohesion: 0.11
Nodes (31): cascade_lookup(), looks_like_action_request(), Cascata com bypass de turno pessoal: uma resposta que depende da memória do…, test_atlas_index_drift_falls_back_without_breaking_the_turn(), test_cache_entry_from_previous_unrestricted_policy_is_ignored(), Atlas, cached(), Turno pessoal não lê nem grava o cache semântico; classificador só no HIT e… (+23 more)

### Community 10 - "Escopo integrado ao turno"
Cohesion: 0.12
Nodes (33): has_catalog_anchor(), A mensagem cita algo do catálogo (categoria de produto, "produto", "catálogo")?…, LLMGateway, O veredito de escopo (embedding) decide ANTES de gastar LLM; a faixa ambígua…, Responde ao classificador de segurança e ao de roteamento conforme o teste…, RoutingLLM, test_a_crashing_classifier_never_drops_the_turn(), test_a_generic_recommend_verb_alone_can_be_refused_by_a_decisive_out_verdict() (+25 more)

### Community 11 - "Escopo por embedding"
Cohesion: 0.10
Nodes (29): best_scores(), classify(), decide(), DataStore, Classificador de ESCOPO — "esta mensagem é assunto da loja?" — feito no…, Regra pura (testável sem Atlas). Devolve (escopo, margem do líder sobre o…, Melhor score por rótulo entre os vizinhos, ou None se não deu para consultar…, Devolve {scope: in|out|chat|unsure, margin, in_score, out_score, chat_score,… (+21 more)

### Community 12 - "Isolamento de banco de teste"
Cohesion: 0.09
Nodes (31): allow_demo_write(), DemoDatabaseRefused, ensure_seeded(), guard(), _indexes_ready(), main(), open_test_store(), _probe_indexes() (+23 more)

### Community 13 - "Test Live Random"
Cohesion: 0.12
Nodes (17): get_settings(), seed_documents(), main(), Restaura os saldos que a própria demo/eval consome (idempotente, só as contas…, restore(), create_search_indexes(), main(), Seed idempotente do plano de dados e do plano de coordenação. (+9 more)

### Community 14 - "Orquestração do turno"
Cohesion: 0.14
Nodes (20): API da PoV multi-agente., ChatResponse, TimelineEvent, _next_steps(), OrchestrationService, TurnBudget, Próximos passos do turno, sempre ancorados em documento existente. Falha aqui…, Uma linha: a chave do agente, `conversa` ou `nenhum`. Classificar é decisão,… (+12 more)

### Community 15 - "Troca de produto"
Cohesion: 0.12
Nodes (23): order_replacement_chain(), Cadeia de trocas do pedido, via $graphLookup no Atlas (loop em Python só em…, build_decision_doc(), new_decision_id(), Spine de decisão e auditoria — o registro imutável do que o sistema decidiu, e…, Monta o documento de decisão. Não grava — quem grava é `record_decision`., apply_replacement(), assess_replacement() (+15 more)

### Community 16 - "Fila de revisão humana"
Cohesion: 0.19
Nodes (21): DataStore, Settings, Uma porta pequena para Atlas com fallback determinístico para testes locais., Schema-at-boundary: cada handoff/trace é validado pelo próprio MongoDB, não só…, list_reviews(), override_rate(), Resolve a revisão, repetindo (via `run_in_transaction_with_retry`) enquanto o…, Taxa de override: de todas as revisões resolvidas, em quantas o humano decidiu… (+13 more)

### Community 17 - "Políticas de escrita segura"
Cohesion: 0.18
Nodes (22): guarded_order_update(), GuardedStatusError, public_document(), Any, Reconstrói o filtro inteiro; nenhuma opção fornecida pelo modelo sobrevive., Tentativa de escrever, pelo caminho genérico, um status que exige regra de…, Caminho genérico de escrita de status. Reconstrói filtro e update no servidor., Escrita de um status guardado. **Uso exclusivo de `app.replacement`** — é ela… (+14 more)

### Community 18 - "Warmup do cache"
Cohesion: 0.16
Nodes (13): Warmup automático do cache semântico: a demo abre e o cache já está quente.…, Dispara em segundo plano e devolve o estado atual na hora (a UI não espera o…, WarmupService, FakeOrchestrator, Warmup automático: aquece perguntas GENÉRICAS por área (as únicas que o cache…, service(), test_a_failed_run_can_be_retried_immediately(), test_concurrent_triggers_share_one_run() (+5 more)

### Community 19 - "01 Chat Home"
Cohesion: 0.10
Nodes (24): Agent Control Plane app shell (nav Chat/Agentes/Guardrails/Metricas, identity picker, live + Atlas status pills), Inspector list of the 8 seeded agents on claude-haiku-4-5, Design decision: empty state pre-announces the coordination view instead of hiding it, KPI strip: agentes ativos, handoffs no turno, origem da rota, tokens estimados, Chat Home Screenshot (empty state), Three-pane turn layout: Canal do Cliente / Raio-X do Turno / Inspetor MongoDB, 'Agentes em acao' chain strip: Suporte to Produtos to Pedidos to Logistica to Pedidos, Rationale: capture from page top so chain strip and collections row both appear, after a real 5-hop run (+16 more)

### Community 20 - "Orçamento de tokens do turno"
Cohesion: 0.14
Nodes (13): BudgetExceeded, Troca a estimativa heurística (chars/4) pelo uso REAL reportado pela API.…, TurnBudget, SlidingWindowLimiter, generate(), main(), Gera o conjunto de SITUAÇÕES (tests/data/situations.json) para medir o agente…, split_of() (+5 more)

### Community 21 - "Configuração e segredos"
Cohesion: 0.13
Nodes (17): cascade_store_turn(), Grava sempre em curto_prazo e só promove respostas estáveis ao cache semântico.…, field_validator, Configuração central; segredos vêm somente do ambiente., Settings, test_foreign_conversation_id_is_replaced_instead_of_hijacked(), test_global_cache_requires_explicit_safe_eligibility(), test_personalized_intent_stays_session_scoped_and_never_leaks() (+9 more)

### Community 22 - "Respostas de orientação"
Cohesion: 0.11
Nodes (22): blocked_reply(), build_suggestions(), greeting_reply(), _in_transit(), is_meta_question(), is_thanks(), looks_like_own_pii(), meta_reply() (+14 more)

### Community 23 - "Economia do gateway de LLM"
Cohesion: 0.15
Nodes (16): LLMGateway, Explicit per-model protocol routing through Grove, with a per-endpoint breaker., parametrize, A API rejeita bloco de texto vazio (BadRequestError). Contexto dinâmico vazio é…, Classificação precisa ser determinística (temperature 0). Nem todo modelo…, test_cache_hit_preserves_replay_but_does_not_count_old_operations(), test_empty_dynamic_context_never_sends_an_empty_system_block(), test_fallback_records_each_attempt_without_exposing_prompts() (+8 more)

### Community 24 - "Cadeia de trocas ($graphLookup)"
Cohesion: 0.10
Nodes (12): build_order_chain_pipeline(), Travessia de grafo sobre `orders`: cadeia de trocas de um pedido. Um pedido…, Segue replacement_order_id -> order_id a partir de um pedido, até `max_depth`…, Traduz a cadeia crua em sinais de negócio. Sem LLM: é aritmética sobre o array., Mesma travessia em Python, para DEMO_MODE/CI — é literalmente o loop que o…, summarize_order_chain(), traverse_order_chain_in_memory(), _store_com_pedidos() (+4 more)

### Community 25 - "Resiliência do supervisor"
Cohesion: 0.11
Nodes (19): Estado do supervisor para ESTE turno: teto de passos, timeout e detector de…, _supervisor_state(), agent_timeout_seconds(), degraded_reply(), _flag(), graceful_degradation(), loop_guard_repeats(), LoopGuard (+11 more)

### Community 26 - "Consultas MongoDB do briefing"
Cohesion: 0.12
Nodes (19): Not LangGraph (hand-written orchestration), cache_autoembed_v1 index, cascade.py, $vectorSearch + $unionWith cascade, graph.py build_order_chain_pipeline, $graphLookup replacement chain, kb_lexical_v1 index, kb_autoembed_v1 index (+11 more)

### Community 27 - "DataStore e fronteira de tools"
Cohesion: 0.19
Nodes (9): _compare(), _driver_session(), _matches(), Desembrulha o handle para o que o pymongo espera receber em `session=`., Como o Mongo: campo ausente/de outro tipo não casa em comparação (em vez de…, Live feed de handoffs do cliente: Change Stream no Atlas, poll no modo…, call_tool(), Executa UMA tool com span, ponto de caos, circuit breaker e (opt-in) teto de… (+1 more)

### Community 28 - "API FastAPI"
Cohesion: 0.17
Nodes (19): agents(), decisions(), eval_runs(), get_metrics(), guardrails(), handoffs(), health(), inspector() (+11 more)

### Community 29 - "Pov Agent Memory Mongodb Template"
Cohesion: 0.13
Nodes (20): Design: dark hero + JSON code card, three-column body, numbered benefit strip, Long-term Memory (episodic, semantic, procedural), Claim: Agent Memory e uma hierarquia de memorias, nao uma collection unica, Memory Engineering Stack (document model, automated embedding, Vector Search, Search+RRF, TTL, Change Streams), recall(): working -> cache -> long_term, vector + lexical + tenant filters, Shared Memory — camada transversal (ai_brain + multi_agent_poc), Short-term Memory (working memory + semantic cache), Slide: Uma plataforma de memoria — Agent Memory (template MongoDB) (+12 more)

### Community 30 - "Test Live Scenarios"
Cohesion: 0.16
Nodes (18): customer_of(), env(), memory_events(), prices(), prime_global_cache(), fixture, parametrize, Bateria LIVE por usuário (ana, bruno, carla, diego): cache semântico, memória… (+10 more)

### Community 31 - "Ataques fim-a-fim"
Cohesion: 0.22
Nodes (16): fact(), facts_of(), LLMGateway, parametrize, Ataques fim-a-fim (orquestrador real, DEMO_MODE, LLM roteirizado): memória…, Só o extrator responde (JSON roteirizado); demais agentes caem no template…, ScriptedLLM, test_episode_memory_cannot_carry_user_text_into_prompts() (+8 more)

### Community 32 - "Dependências do frontend"
Cohesion: 0.11
Nodes (18): dependencies, react, react-dom, vite, @vitejs/plugin-react, devDependencies, name, private (+10 more)

### Community 33 - "Trilha de decisões"
Cohesion: 0.23
Nodes (17): build_audit_event(), decision_trail(), Any, Grava a decisão e, junto, o evento de auditoria correspondente. Os dois inserts…, Trilha completa de um cliente (ou de um pedido): decisões + eventos, mais…, record_decision(), _decision(), parametrize (+9 more)

### Community 34 - "Trace do turno (Langfuse)"
Cohesion: 0.15
Nodes (10): Any, build_turn_trace(), get_langfuse(), _NoopLangfuse, _NoopTrace, Sem chave configurada (ou Langfuse fora do ar): instrumentação vira no-op,…, Uma trace por turno cobrindo a timeline INTEIRA — roteamento, decisão de cache,…, _jsonable() (+2 more)

### Community 35 - "Fora de escopo e saudação"
Cohesion: 0.21
Nodes (14): CountingLLM, LLMGateway, parametrize, Perguntas aleatórias: o sistema reconhece o que está fora do escopo, responde…, test_a_mixed_turn_is_never_promoted_to_the_shared_cache(), test_attack_wrapped_in_a_random_question_reaches_the_classifier_and_is_blocked(), test_greetings_and_capability_questions_get_the_welcome_not_a_refusal(), test_legitimate_requests_are_recognised_as_in_scope() (+6 more)

### Community 36 - "Crash-resume com SIGKILL"
Cohesion: 0.20
Nodes (15): AsyncClient, _child_env(), _cleanup(), contextlib_suppress(), _ensure_test_data(), Cenário de caos que precisa de processo de verdade: SIGKILL no meio de uma…, O banco de teste precisa existir e ter as identidades do seed (o token sai de…, Remove o que este cenário escreveu — nem o banco de teste fica com conversa… (+7 more)

### Community 37 - "Eval de roteamento"
Cohesion: 0.22
Nodes (15): _customers(), embedding_evidence(), _expected(), main(), DataStore, Eval de roteamento multiagente: acurácia de rota, taxa de resolução e handoffs…, Prova, no próprio relatório, se o caminho de EMBEDDING estava vivo nesta…, Agente de ENTRADA do turno — roteamento é a primeira decisão, não o fim da… (+7 more)

### Community 38 - "Regressão de caos"
Cohesion: 0.21
Nodes (15): _assert_scenario(), Regressão permanente dos cenários de caos (mesma implementação de…, test_concurrent_requests_on_one_conversation_do_not_corrupt_state(), test_failing_tool_opens_its_circuit(), test_hung_agent_is_interrupted_by_the_supervisor(), test_legacy_flag_restores_the_old_500_behaviour(), test_loop_guard_escalates_to_a_human(), test_malformed_tool_payload_never_invents_data() (+7 more)

### Community 39 - "Mapa de agentes"
Cohesion: 0.18
Nodes (15): ai_brain.agent_registry, billing_agent, kb_articles hybrid search, logistics_agent, loyalty_accounts collection, loyalty_agent, order_agent, product_agent (+7 more)

### Community 40 - "Injeção de falha"
Cohesion: 0.19
Nodes (12): _armed(), ChaosProviderError, enabled(), hook(), mangle(), Exception, Injeção de falha controlada — DESLIGADA salvo `CHAOS=1` no ambiente. O PoV…, Zera o contador de disparos (um teste por cenário). (+4 more)

### Community 41 - "Contratos de resposta"
Cohesion: 0.20
Nodes (12): update_agent(), AgentUpdate, ChatRequest, OrderStatusUpdate, Próximo passo clicável, sempre derivado de um documento que existe., Resolução de um caso escalado. `decision` é fechada: o analista escolhe entre…, ReviewResolution, Suggestion (+4 more)

### Community 42 - "JWT e mascaramento"
Cohesion: 0.18
Nodes (11): get_store(), current_customer(), issue_token(), Depends, Request, request_identity_key(), require_admin(), secrets_equal() (+3 more)

### Community 43 - "Roteamento determinístico"
Cohesion: 0.21
Nodes (12): out_of_scope_reply(), Mensagem fora do domínio de atendimento — o caso 'pergunta sem sentido'. Não…, has_domain_signal(), has_weak_signal(), out_of_scope_sentences(), True quando a mensagem tem sinal FORTE de que fala com esta loja., Só palavras genéricas (ajuda, conta, valor...) — inconclusivo sem o…, Numa mensagem MISTA (várias frases, ao menos uma da loja), as frases sem nenhum… (+4 more)

### Community 44 - "Roteamento determinístico (2)"
Cohesion: 0.23
Nodes (11): cheap_route(), detect_fanout(), deterministic_orchestrator(), _padded(), Texto sem acento e sem pontuação, com espaço nas bordas: permite casar palavra…, Resolve somente regras inequívocas; empates vão para o orquestrador., Pattern 'Parallel Fan-Out': pedido composto ('status do pedido e quanto devo')…, RouteDecision (+3 more)

### Community 45 - "Adr 001 Arquitetura Multi Agente"
Cohesion: 0.18
Nodes (13): ADR-001 Coordenacao multi-agente orientada a documentos, ADR-002 Memoria LLM e turno pessoal, ADR-003 Guardrail em duas faixas, ADR-004 Escopo por embedding e medicao, agent_conversations, ai_brain.agent_registry, Parallel fan-out order + billing, agent_handoffs / agent_traces (+5 more)

### Community 46 - "Mapa de agentes (2)"
Cohesion: 0.17
Nodes (12): cheap_route (router.py), orchestrator, Pendencias conhecidas, reaches_scope_classifier, ROUTER_PROMPT, scope_classifier.py (in/out/chat), scope_probes collection (214), scope_probes_vs index (+4 more)

### Community 47 - "Tracing por span"
Cohesion: 0.17
Nodes (7): active(), _NoSpan, Tracing distribuído opt-in, em cima de `tracing` do _shared (pov-shared 0.1.4).…, Liga o tracing conforme TRACE_SINK. Fail-open: erro aqui nunca impede o app de…, Tokens e custo estimado de UMA chamada, no span dela., record_llm_usage(), setup_tracing()

### Community 48 - "Busca híbrida e vetorial"
Cohesion: 0.26
Nodes (10): build_kb_lexical_pipeline(), build_kb_rank_fusion_pipeline(), build_kb_vector_pipeline(), Combina rankings lexical e vetorial sem comparar escalas de score. Continua…, Perna semântica: Atlas Vector Search com Automated Embedding (voyage-4)., Perna lexical: BM25 com boost no título (analyzer português)., Híbrido server-side: $rankFusion funde as duas pernas dentro do banco (MongoDB…, reciprocal_rank_fusion() (+2 more)

### Community 49 - "Adr 004 Escopo Por Embedding E Medicao P"
Cohesion: 0.20
Nodes (12): ADR-002 LLM memory and personal turn, ADR-003 two-band guardrail, Baseline before ADR-004 (n=229), ADR-004 decision (scope by embedding), router.DOMAIN_VOCAB word list (ADR-003), Margin-based decision rule, Missing-label bounded by last neighbour, No-verdict fallback to word list (+4 more)

### Community 50 - "Adr 004 Escopo Por Embedding E Medicao P (2)"
Cohesion: 0.17
Nodes (12): Set growth to 287, calibrate_thresholds.py --only scope, generate_situations.py (--append), Precision-first thresholds, floor 0.04, Async reindex on adding probes, Outlier 'o roteador que adquiri nao conecta', Small samples, scope_classifier_config (+4 more)

### Community 51 - "Test Cache Eligibility"
Cohesion: 0.29
Nodes (10): cascade_long_term_context(), MISS nos dois: puxa contexto de longo prazo (memória episódica do cliente) pro…, Cache útil E seguro: memória estruturada do cliente não bloqueia pergunta…, O cache global guarda a resposta SEM orçamento; servi-la a quem tem teto…, test_customer_with_budget_never_receives_the_generic_cached_recommendation(), test_generic_answer_is_cached_even_for_customer_with_facts_and_history(), test_global_cache_serves_other_customers_the_generic_answer(), test_only_structured_episodes_reach_the_prompt() (+2 more)

### Community 52 - "API FastAPI (2)"
Cohesion: 0.24
Nodes (11): chat(), _degraded_turn(), demo_reset(), demo_scenarios(), events_stream(), Degradação graciosa no topo: o turno falhou, mas o cliente recebe estado…, Desfaz o que a demo gravou NESTE cliente (customer_key do JWT, nunca do corpo)…, Roteiro versionado no plano de coordenação; UI, warmup e eval usam a mesma… (+3 more)

### Community 53 - "Test Live Stream"
Cohesion: 0.29
Nodes (7): handoff_event_stream(), Adapt the Change Stream to SSE with immediate confirmation and heartbeats., ConnectedRequest, IdleStore, OneHandoffStore, test_sse_confirms_connection_before_first_handoff_and_then_emits_data(), test_sse_sends_heartbeat_while_change_stream_is_idle()

### Community 54 - "Eval por situações"
Cohesion: 0.25
Nodes (9): compare(), main(), outcome_of(), Mede o agente REAL (Atlas + LLM) contra tests/data/situations.json — o que um…, O que o cliente viu: bloqueado, orientação de escopo, boas-vindas ou qual…, Taxas que importam ao cliente, separadas de acerto de rótulo., report(), run() (+1 more)

### Community 55 - "Grove Costs 2026 09 18"
Cohesion: 0.20
Nodes (11): Claude Haiku 4.5 (Anthropic) - $1.41, 25.2% of cost, Claude Opus 4.8 (Anthropic) - $0.18, 3.2% of cost, Claude Opus 5 (Anthropic) - $0.0015, 0.0% of cost, Claude Sonnet 4.5 (Anthropic) - $1.24, 22.2% of cost, Claude Sonnet 4.6 (Anthropic) - $2.09, 37.3% of cost, Claude Sonnet 5 (Anthropic) - $0.65, 11.7% of cost, GitHub Copilot (usage source), GPT-5.3 Codex (OpenAI) - $0.02, 0.4% of cost (+3 more)

### Community 56 - "Adr 004 Escopo Por Embedding E Medicao P (3)"
Cohesion: 0.20
Nodes (10): LLM security classifier + self-reinforcing write-back, guardrails.needs_security_review, customer_key isolation safety net, Final result (287 situations), guardrails.needs_security_review, Out-of-scope orientation (0 tokens), Routing LLM before security (ambiguous, no suspicion), Security before agent outside keyword route (+2 more)

### Community 57 - "Guardrails de borda"
Cohesion: 0.24
Nodes (9): set_store(), enabled(), mask_log(), Guardrails de BORDA usando o pacote comum (`guardrails` do _shared), opt-in por…, Mascara PII em todo valor de texto de um evento de log., Valida a resposta serializada contra o próprio schema. Nunca derruba o turno., validate_response(), lifespan() (+1 more)

### Community 58 - "Comportamento dos agentes (briefing)"
Cohesion: 0.20
Nodes (9): agent_conversations, agent_handoffs, agent_traces, Manual checkpointing collections, short_term_memory (24h), turn_classifier (turn_probes, 0.7162), Collections in action panel, Memory/cache demo chips (+1 more)

### Community 59 - "Mapa de agentes (3)"
Cohesion: 0.22
Nodes (9): ADR-001 multi-agent architecture, ADR-002 LLM memory and personal turn, ADR-003 two-band guardrail and out-of-scope, ADR-004 scope by embedding + situations, eval_situations.py, generate_situations.py (--append), looks_like_instruction filter, LLM memory extractor (memory.py) (+1 more)

### Community 60 - "Gateway de LLM"
Cohesion: 0.22
Nodes (3): _CircuitBreaker, TurnBudget, False quando o circuito está aberto e ainda dentro da janela de curto-circuito.

### Community 61 - "API FastAPI (3)"
Cohesion: 0.28
Nodes (9): budget_handler(), log(), Exception, request_context(), unhandled_error_handler(), BudgetExceeded, exception_handler, middleware (+1 more)

### Community 62 - "Resiliência do supervisor (2)"
Cohesion: 0.22
Nodes (5): Span com latência medida. Vira um no-op quando o tracing está desligado., span(), guarded_tool(), Fronteira de UMA tool: span, ponto de caos e (opt-in) circuit breaker., _ToolCircuit

### Community 63 - "Respostas de orientação (2)"
Cohesion: 0.25
Nodes (8): is_capabilities_question(), is_greeting(), Minúsculas, sem acento, pontuação virando espaço: "Bom dia, tudo bem?" → "bom…, Cumprimento/abertura de conversa — curto e sem pedido embutido., O que você faz?" é pergunta sobre o atendimento, não assunto alheio: responde…, _words(), test_capability_questions_are_answered_not_refused(), test_greetings_survive_punctuation()

### Community 64 - "Golden eval (caixa-preta)"
Cohesion: 0.39
Nodes (7): grade_case(), grade_outcome(), main(), Eval harness: roda o golden dataset (app/seed_data.py:EVAL_CASES) contra o…, run(), snapshot(), .githooks/pre-push (ruff + offline + live)

### Community 65 - "Adr 004 Escopo Por Embedding E Medicao P (4)"
Cohesion: 0.29
Nodes (8): Ambiguous band goes to LLM (unsure), `conversa` exit, Dev/holdout split by message hash, eval_situations.py, LLM-generated set bias, New regressions enter situations.json, orchestration.ROUTER_PROMPT, situations.json (229 -> 287 / 33 -> 39 categories)

### Community 66 - "API FastAPI (4)"
Cohesion: 0.29
Nodes (7): approve_candidate(), create_token(), Aquece o cache em segundo plano e responde na hora. Aberto de propósito (a UI…, Fecha a pausa: grava a decisão humana (imutável) e devolve o caso ao agente. O…, resolve_pending_review(), warmup(), post

### Community 67 - "Test Security Config"
Cohesion: 0.48
Nodes (6): Fail startup on configurations that would expose demo credentials., validate_runtime_security(), production_settings(), parametrize, test_insecure_production_configuration_is_rejected(), test_secure_production_configuration_is_accepted()

### Community 68 - "Adr 002 Memoria Llm E Turno Pessoal"
Cohesion: 0.29
Nodes (7): ADR-002 Memória por LLM e turno pessoal, Budget pre-filter (max_price_brl in $vectorSearch), Long-term episode memory (system labels only), looks_like_instruction, LLM memory extractor with supersession, Personal-turn gates and turn classifier, Semantic cache cascade (short-term/session/customer/global)

### Community 69 - "Agent Quality Economics"
Cohesion: 0.29
Nodes (7): claude-haiku-4-5 model, eval.py avaliador, eval_runs collection, gpt-5.6-luna model, grove-mixed-live eval run, bruno-paraphrase-exfiltration eval case, ana-paraphrase-jailbreak eval case

### Community 70 - "Mapa de agentes (4)"
Cohesion: 0.33
Nodes (6): calibrate_thresholds.py, scope_classifier_config, seed_turn_probes.py, turn_classifier (threshold 0.7162), vector_block_threshold = 0.8814, vector_threshold

### Community 71 - "Mapa de agentes (5)"
Cohesion: 0.33
Nodes (6): DEMO_MODE in-memory DataStore, denylist_autoembed_v1 semantic denylist, GROUNDING_RULES, llm_synthesize grounded responses, overlap_score (Jaccard), Static denylist + near-miss

### Community 73 - "Smoke caixa-preta"
Cohesion: 0.47
Nodes (5): check(), main(), Client, Smoke test contra a API no ar. Uso: python tests/smoke.py [URL]., token()

### Community 74 - "Guia do repositório"
Cohesion: 0.33
Nodes (5): Architecture, Commands, Continuidade da revisão de resiliência, Known gaps (verified against code, not just docs), Project

### Community 75 - "Agent Quality Economics (2)"
Cohesion: 0.40
Nodes (6): Grove Gateway, llm_calls ledger, LLM_PRICES config, Fórmula de custo por chamada (tarifas separadas), Fórmula de estimativa por média histórica, Grove Gateway captured costs table

### Community 76 - "Baseline de testes"
Cohesion: 0.33
Nodes (6): Baseline da suíte offline (commit f279bfc), tests/test_auto_warmup.py, tests/test_budget_policy.py, tests/test_cache_isolation.py, tests/test_calibration.py, tests/test_concurrency.py

### Community 77 - "Mapa de agentes (6)"
Cohesion: 0.40
Nodes (4): Architecture, Commands, Known gaps (verified against code, not just docs), Project

### Community 78 - "DataStore e fronteira de tools (2)"
Cohesion: 0.40
Nodes (4): Só para pipelines reais ($vectorSearch/$unionWith) — sem equivalente em…, Tool curto-circuitada: o chamador degrada em vez de pagar mais uma falha., ToolOpenCircuit, RuntimeError

### Community 79 - "DataStore e fronteira de tools (3)"
Cohesion: 0.40
Nodes (3): Escrita de negócio e registro de decisão como uma coisa só. O problema que isto…, Handle de uma transação em curso. `driver_session` é a sessão do pymongo, ou…, Transaction

### Community 81 - "Adr 003 Guardrail Em Duas Faixas"
Cohesion: 0.40
Nodes (5): ADR-002 Memoria LLM e turno pessoal, ADR-003 Guardrail em duas faixas e fora de escopo, ADR-003 discarded alternatives, Domain vocabulary (DOMAIN_VOCAB / has_domain_signal), Out-of-scope handling (deterministic)

### Community 82 - "Mcp"
Cohesion: 0.40
Nodes (4): MDB_MCP_CONNECTION_STRING, npx, mongodb, mongodb-mcp-server

### Community 84 - "Slide Docs Brief"
Cohesion: 0.50
Nodes (3): ADR-001-arquitetura-multi-agente.md, Documentação dividida por leitor, Documentação faltante (RUNBOOK, data-model, ADR-002+, SECURITY.md)

### Community 85 - "Grove Costs 2026 09 19"
Cohesion: 0.67
Nodes (4): Claude Haiku 4.5 (Anthropic) usage row, GPT-5.6 Luna (OpenAI) usage row, Usage by Model cost table (Grove gateway dashboard), Grove gateway (Anthropic APIM) — PoV LLM access layer

### Community 87 - "Escopo do PoV"
Cohesion: 0.67
Nodes (3): Escopo do PoV multiagente-atendimento, Orquestração manual em Python async (sem LangGraph), Portas estritas 8031 / 5191

### Community 88 - "Mapa de agentes (7)"
Cohesion: 0.67
Nodes (3): Known gaps, Langfuse build_turn_trace, SSE + Change Stream + op counters

### Community 92 - "Grove Cost Guide"
Cohesion: 0.67
Nodes (3): LLM_BLENDED_PRICES config, Premissa histórica 18/09/2026 (substituída), Regra vigente 19/09/2026 (LLM_BLENDED_PRICES)

### Community 94 - "Ci"
Cohesion: 0.67
Nodes (3): Backend tests and lint job, CI Workflow, Frontend build job

## Ambiguous Edges - Review These
- `MODO ADMIN toggle gating per-agent enable/disable switches` → `Principle: input validated once per turn, before any model, memory or trace`  [AMBIGUOUS]
  docs/screenshots/04-agents-registry.png · relation: conceptually_related_to
- `GPT-5.3 Codex (OpenAI) - $0.02, 0.4% of cost` → `Grove Gateway (usage source)`  [AMBIGUOUS]
  docs/internal/assets/grove-costs-2026-09-18.png · relation: shares_data_with

## Knowledge Gaps
- **195 isolated node(s):** `_FakeBlock`, `_FakeUsage`, `start.sh script`, `devDependencies`, `name` (+190 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 659 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **61 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `MODO ADMIN toggle gating per-agent enable/disable switches` and `Principle: input validated once per turn, before any model, memory or trace`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `GPT-5.3 Codex (OpenAI) - $0.02, 0.4% of cost` and `Grove Gateway (usage source)`?**
  _Edge tagged AMBIGUOUS (relation: shares_data_with) - confidence is low._
- **Why does `DataStore` connect `Fila de revisão humana` to `Memória do cliente (LLM)`, `Agentes especializados`, `Bateria de caos`, `Classificador de turno pessoal`, `Guardrail de entrada e saída`, `Turno pessoal fora do cache`, `Test Live Random`, `Orquestração do turno`, `Troca de produto`, `Warmup do cache`, `Configuração e segredos`, `Respostas de orientação`, `Economia do gateway de LLM`, `DataStore e fronteira de tools`, `API FastAPI`, `Test Live Scenarios`, `Ataques fim-a-fim`, `Trilha de decisões`, `Fora de escopo e saudação`, `Crash-resume com SIGKILL`, `Contratos de resposta`, `JWT e mascaramento`, `Test Cache Eligibility`, `API FastAPI (2)`, `Test Live Stream`, `Guardrails de borda`, `API FastAPI (4)`, `DataStore e fronteira de tools (2)`, `DataStore e fronteira de tools (3)`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Why does `Settings` connect `Configuração e segredos` to `Memória do cliente (LLM)`, `Agentes especializados`, `Trace do turno (Langfuse)`, `Trilha de decisões`, `Fora de escopo e saudação`, `Test Security Config`, `Classificador de turno pessoal`, `Guardrail de entrada e saída`, `Turno pessoal fora do cache`, `JWT e mascaramento`, `Test Live Random`, `Orquestração do turno`, `Fila de revisão humana`, `Warmup do cache`, `Test Cache Eligibility`, `Ataques fim-a-fim`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Why does `OrchestrationService` connect `Orquestração do turno` to `Fora de escopo e saudação`, `Bateria de caos`, `Classificador de turno pessoal`, `Escopo integrado ao turno`, `Test Live Random`, `Fila de revisão humana`, `Test Cache Eligibility`, `Configuração e segredos`, `Eval por situações`, `Economia do gateway de LLM`, `Guardrails de borda`, `API FastAPI`, `Test Live Scenarios`, `Ataques fim-a-fim`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Are the 64 inferred relationships involving `DataStore` (e.g. with `order_replacement_chain()` and `run_billing_agent()`) actually correct?**
  _`DataStore` has 64 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `Settings` (e.g. with `build_turn_trace()` and `get_langfuse()`) actually correct?**
  _`Settings` has 6 INFERRED edges - model-reasoned connections that need verification._