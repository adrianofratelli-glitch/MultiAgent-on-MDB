# Graph Report - multiagente-atendimento  (2026-09-22)

## Corpus Check
- 26 files · ~200,430 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1683 nodes · 3404 edges · 158 communities (96 shown, 60 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 200 edges (avg confidence: 0.9)
- Token cost: 62,000 input · 26,000 output

## Community Hubs (Navigation)
- Memória do cliente (LLM)
- Fora de escopo e saudação
- Documento de arquitetura
- Isolamento de banco de teste
- Frontend da demo
- Bateria de caos
- Guardrail de entrada e saída
- Escopo integrado ao turno
- Turno pessoal fora do cache
- Agentes especializados
- Trilha de decisões
- Orçamento do cliente no catálogo
- Respostas de orientação
- Políticas de escrita segura
- Fila de revisão humana
- Classificador de turno pessoal
- Warmup do cache
- 01 Chat Home
- Orçamento de tokens do turno
- Economia do gateway de LLM
- Test Live
- Cadeia de trocas ($graphLookup)
- Resiliência do supervisor
- Calibração medida de limiares
- Consultas MongoDB do briefing
- Cascata semântica de cache
- Test Cache Isolation
- API FastAPI
- Orquestração do turno
- Pov Agent Memory Mongodb Template
- Ataques fim-a-fim
- Dependências do frontend
- Calibração medida de limiares (2)
- Injeção de falha
- DataStore e fronteira de tools
- Guia do repositório
- Regressão de caos
- Mapa de agentes
- Troca de produto
- Escopo por embedding
- Test Concurrency
- Contratos de resposta
- Migrate Legacy Memory
- Tracing por span
- Escopo por embedding (2)
- Adr 004 Escopo Por Embedding E Medicao P
- Seed e índices Atlas
- Atritos com o _shared
- Adr 001 Arquitetura Multi Agente
- Mapa de agentes (2)
- Golden eval
- Trace do turno (Langfuse)
- Busca híbrida e vetorial
- JWT e mascaramento
- Eval de roteamento
- Adr 004 Escopo Por Embedding E Medicao P (2)
- API FastAPI (2)
- Test Cache Eligibility
- API FastAPI (3)
- Test Live Stream
- Eval por situações
- Guia do repositório (2)
- Relatório de caos
- Grove Costs 2026 09 18
- Gateway de LLM
- Baseline de testes
- Adr 004 Escopo Por Embedding E Medicao P (3)
- Comportamento dos agentes (briefing)
- Mapa de agentes (3)
- Resiliência do supervisor (2)
- Test Live Random
- Adr 004 Escopo Por Embedding E Medicao P (4)
- Agentes especializados (2)
- Guardrails de borda
- API FastAPI (4)
- Test Security Config
- Métricas em processo
- Probes de escopo
- Formato do eval
- Adr 002 Memoria Llm E Turno Pessoal
- Agent Quality Economics
- Mapa de agentes (4)
- Mapa de agentes (5)
- Smoke caixa-preta
- Guia do repositório (3)
- Agent Quality Economics (2)
- Mapa de agentes (6)
- Contratos de resposta (2)
- DataStore e fronteira de tools (2)
- Adr 003 Guardrail Em Duas Faixas
- Mcp
- DataStore e fronteira de tools (3)
- Resiliência do supervisor (3)
- Slide Docs Brief
- Grove Costs 2026 09 19
- Http Deadline Test
- Mapa de agentes (7)
- Consulta de spans
- Warmup do cache (2)
- Grove Cost Guide
- Ci
- Mapa de agentes (8)
- Mapa de agentes (9)
- Agentes especializados (3)
- Test Concurrency (2)
- Test Concurrency (3)
- Test Fuzz Memory
- Documento de arquitetura (2)
- Comportamento dos agentes (briefing) (2)
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
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Requirements
- Requirements (2)
- Requirements (3)
- Requirements (4)
- Community 135
- Community 136
- Community 137
- Adr 003 Guardrail Em Duas Faixas (2)
- Adr 003 Guardrail Em Duas Faixas (3)
- Adr 003 Guardrail Em Duas Faixas (4)
- Adr 003 Guardrail Em Duas Faixas (5)
- Adr 004 Escopo Por Embedding E Medicao P (5)
- Documento de arquitetura (4)
- Documento de arquitetura (5)
- Documento de arquitetura (6)
- Comportamento dos agentes (briefing) (3)
- Comportamento dos agentes (briefing) (4)
- Comportamento dos agentes (briefing) (5)
- Comportamento dos agentes (briefing) (6)
- Comportamento dos agentes (briefing) (7)
- Comportamento dos agentes (briefing) (8)
- Consultas MongoDB do briefing (2)
- Consultas MongoDB do briefing (3)
- Ui Flows (2)
- Ui Flows (3)
- Community 156
- Community 157

## God Nodes (most connected - your core abstractions)
1. `DataStore` - 184 edges
2. `Settings` - 81 edges
3. `utcnow()` - 51 edges
4. `OrchestrationService` - 45 edges
5. `cascade_lookup()` - 33 edges
6. `LLMGateway` - 31 edges
7. `get_settings()` - 30 edges
8. `TimelineEvent` - 28 edges
9. `active_budget()` - 25 edges
10. `world()` - 25 edges

## Surprising Connections (you probably didn't know these)
- `turn_classifier.py` --semantically_similar_to--> `turn_classifier (elegibilidade de cache por vetor)`  [INFERRED] [semantically similar]
  docs/briefing/architecture.md → CLAUDE.md
- `scope_classifier.py` --semantically_similar_to--> `scope_classifier (escopo por embedding)`  [INFERRED] [semantically similar]
  docs/briefing/architecture.md → CLAUDE.md
- `turn_classifier (turn_probes, 0.7162)` --references--> `turn_classifier (elegibilidade de cache por vetor)`  [INFERRED]
  docs/briefing/agent-behavior.md → CLAUDE.md
- `eval_situations.py / generate_situations.py` --semantically_similar_to--> `situations.json (287 situações, dev/holdout)`  [INFERRED] [semantically similar]
  docs/briefing/architecture.md → CLAUDE.md
- `eval/routing_dataset.json (24 casos sintéticos)` --semantically_similar_to--> `situations.json (287 situações, dev/holdout)`  [INFERRED] [semantically similar]
  eval/FORMAT.md → CLAUDE.md

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
- **Pipeline de decisão de um turno** — claude_guardrail_two_band, claude_scope_classifier, claude_cheap_route, claude_semantic_cascade, claude_orchestration_supervisor [EXTRACTED 1.00]
- **Camada de resiliência por padrão** — readme_tool_timeout, readme_tool_breaker, docs_chaos_report_cenario_loop_guard, docs_chaos_report_resilience_call_tool, readme_resiliencia_por_padrao [EXTRACTED 1.00]
- **Medição e calibração (limiares e datasets)** — claude_calibrate_thresholds, claude_situations_dataset, eval_format_routing_dataset, docs_baseline_tests_test_calibration [INFERRED 0.85]

## Communities (158 total, 60 thin omitted)

### Community 0 - "Memória do cliente (LLM)"
Cohesion: 0.06
Nodes (76): cascade_store_episode(), Registra na memória de longo prazo QUE o cliente tratou de um assunto — não o…, Reset da memória DA DEMO de um cliente: deixa o usuário como estava antes de a…, reset_customer_memory(), active_budget(), _active_docs(), active_facts(), _clean_budget() (+68 more)

### Community 1 - "Fora de escopo e saudação"
Cohesion: 0.07
Nodes (45): is_capabilities_question(), is_greeting(), out_of_scope_reply(), Minúsculas, sem acento, pontuação virando espaço: "Bom dia, tudo bem?" → "bom…, Cumprimento/abertura de conversa — curto e sem pedido embutido., O que você faz?" é pergunta sobre o atendimento, não assunto alheio: responde…, Mensagem fora do domínio de atendimento — o caso 'pergunta sem sentido'. Não…, _words() (+37 more)

### Community 2 - "Documento de arquitetura"
Cohesion: 0.06
Nodes (45): agent_registry, warmup.py, billing_agent, Semantic cache cascade, cheap_route, Main components table, decisions.py / reviews.py, DEMO_MODE DataStore (+37 more)

### Community 3 - "Isolamento de banco de teste"
Cohesion: 0.08
Nodes (40): AsyncClient, _child_env(), _cleanup(), contextlib_suppress(), _ensure_test_data(), Cenário de caos que precisa de processo de verdade: SIGKILL no meio de uma…, O banco de teste precisa existir e ter as identidades do seed (o token sai de…, Remove o que este cenário escreveu — nem o banco de teste fica com conversa… (+32 more)

### Community 4 - "Frontend da demo"
Cohesion: 0.06
Nodes (24): api, boundedRequest(), request(), App(), IDENTITIES, NAV, OP_LABELS, AiBrainInspector() (+16 more)

### Community 5 - "Bateria de caos"
Cohesion: 0.09
Nodes (40): Zera o contador de disparos (um teste por cenário)., reset(), circuit_state(), reset_circuits(), _degraded(), env(), _FakeAnthropic, _FakeBlock (+32 more)

### Community 6 - "Guardrail de entrada e saída"
Cohesion: 0.09
Nodes (34): check_input(), check_output(), GuardrailResult, _is_pii_only(), _load_denylist_and_policy(), log_event(), needs_security_review(), overlap_score() (+26 more)

### Community 7 - "Escopo integrado ao turno"
Cohesion: 0.12
Nodes (33): has_catalog_anchor(), A mensagem cita algo do catálogo (categoria de produto, "produto", "catálogo")?…, LLMGateway, O veredito de escopo (embedding) decide ANTES de gastar LLM; a faixa ambígua…, Responde ao classificador de segurança e ao de roteamento conforme o teste…, RoutingLLM, test_a_crashing_classifier_never_drops_the_turn(), test_a_generic_recommend_verb_alone_can_be_refused_by_a_decisive_out_verdict() (+25 more)

### Community 8 - "Turno pessoal fora do cache"
Cohesion: 0.13
Nodes (27): cascade_lookup(), Cascata com bypass de turno pessoal: uma resposta que depende da memória do…, Atlas, cached(), Turno pessoal não lê nem grava o cache semântico; classificador só no HIT e…, Atlas simulado: short_term devolve um HIT; turn_probes devolve o score que o…, Scoped, store_turn() (+19 more)

### Community 9 - "Agentes especializados"
Cohesion: 0.17
Nodes (29): AgentResult, extract_id(), _is_trivial_lookup(), llm_synthesize(), Any, Deixa o modelo redigir a resposta em cima do dado JÁ retornado do Mongo — a…, Modo econômico: pula a chamada real ao Anthropic quando a mensagem é só o…, _requested_status() (+21 more)

### Community 10 - "Trilha de decisões"
Cohesion: 0.14
Nodes (23): DataStore, Settings, Uma porta pequena para Atlas com fallback determinístico para testes locais., Schema-at-boundary: cada handoff/trace é validado pelo próprio MongoDB, não só…, build_audit_event(), decision_trail(), new_decision_id(), Any (+15 more)

### Community 11 - "Orçamento do cliente no catálogo"
Cohesion: 0.14
Nodes (25): build_product_pipeline(), Busca de catálogo no Atlas. O teto de preço entra no `filter` do $vectorSearch…, run_product_agent(), search_products(), demo_store(), FakeAtlas, Orçamento do cliente é campo estruturado: o SERVIDOR injeta o teto como pré-…, Nada cabe no orçamento: a resposta diz isso; nunca mostra item acima do teto… (+17 more)

### Community 12 - "Respostas de orientação"
Cohesion: 0.11
Nodes (24): blocked_reply(), build_suggestions(), format_options(), greeting_reply(), _in_transit(), is_meta_question(), is_thanks(), looks_like_own_pii() (+16 more)

### Community 13 - "Políticas de escrita segura"
Cohesion: 0.18
Nodes (22): guarded_order_update(), GuardedStatusError, public_document(), Any, Reconstrói o filtro inteiro; nenhuma opção fornecida pelo modelo sobrevive., Tentativa de escrever, pelo caminho genérico, um status que exige regra de…, Caminho genérico de escrita de status. Reconstrói filtro e update no servidor., Escrita de um status guardado. **Uso exclusivo de `app.replacement`** — é ela… (+14 more)

### Community 14 - "Fila de revisão humana"
Cohesion: 0.20
Nodes (22): list_reviews(), new_review_id(), open_review(), override_rate(), Any, Escalonamento pausável — o caso para de avançar até um humano decidir. O padrão…, Resolve a revisão, repetindo (via `run_in_transaction_with_retry`) enquanto o…, Taxa de override: de todas as revisões resolvidas, em quantas o humano decidiu… (+14 more)

### Community 15 - "Classificador de turno pessoal"
Cohesion: 0.13
Nodes (18): classify(), Devolve {personal, score, threshold, nearest, method, error, latency_ms}.…, create_index(), main(), Semeia SÓ o classificador de turno pessoal (probes + índice vetorial) —…, Upsert dos probes semeados em <brain_db>.turn_probes. Devolve quantos são novos., seed_probes(), FakeAtlas (+10 more)

### Community 16 - "Warmup do cache"
Cohesion: 0.16
Nodes (13): Warmup automático do cache semântico: a demo abre e o cache já está quente.…, Dispara em segundo plano e devolve o estado atual na hora (a UI não espera o…, WarmupService, FakeOrchestrator, Warmup automático: aquece perguntas GENÉRICAS por área (as únicas que o cache…, service(), test_a_failed_run_can_be_retried_immediately(), test_concurrent_triggers_share_one_run() (+5 more)

### Community 17 - "01 Chat Home"
Cohesion: 0.10
Nodes (24): Agent Control Plane app shell (nav Chat/Agentes/Guardrails/Metricas, identity picker, live + Atlas status pills), Inspector list of the 8 seeded agents on claude-haiku-4-5, Design decision: empty state pre-announces the coordination view instead of hiding it, KPI strip: agentes ativos, handoffs no turno, origem da rota, tokens estimados, Chat Home Screenshot (empty state), Three-pane turn layout: Canal do Cliente / Raio-X do Turno / Inspetor MongoDB, 'Agentes em acao' chain strip: Suporte to Produtos to Pedidos to Logistica to Pedidos, Rationale: capture from page top so chain strip and collections row both appear, after a real 5-hop run (+16 more)

### Community 18 - "Orçamento de tokens do turno"
Cohesion: 0.14
Nodes (13): BudgetExceeded, Troca a estimativa heurística (chars/4) pelo uso REAL reportado pela API.…, TurnBudget, SlidingWindowLimiter, generate(), main(), Gera o conjunto de SITUAÇÕES (tests/data/situations.json) para medir o agente…, split_of() (+5 more)

### Community 19 - "Economia do gateway de LLM"
Cohesion: 0.15
Nodes (16): LLMGateway, Explicit per-model protocol routing through Grove, with a per-endpoint breaker., parametrize, A API rejeita bloco de texto vazio (BadRequestError). Contexto dinâmico vazio é…, Classificação precisa ser determinística (temperature 0). Nem todo modelo…, test_cache_hit_preserves_replay_but_does_not_count_old_operations(), test_empty_dynamic_context_never_sends_an_empty_system_block(), test_fallback_records_each_attempt_without_exposing_prompts() (+8 more)

### Community 20 - "Test Live"
Cohesion: 0.14
Nodes (18): get_settings(), main(), Sincroniza SÓ os roteiros de demo (brain.demo_scenarios) com app/seed_data.py —…, sync(), agent_doc(), extract(), live(), fixture (+10 more)

### Community 21 - "Cadeia de trocas ($graphLookup)"
Cohesion: 0.10
Nodes (12): build_order_chain_pipeline(), Travessia de grafo sobre `orders`: cadeia de trocas de um pedido. Um pedido…, Segue replacement_order_id -> order_id a partir de um pedido, até `max_depth`…, Traduz a cadeia crua em sinais de negócio. Sem LLM: é aritmética sobre o array., Mesma travessia em Python, para DEMO_MODE/CI — é literalmente o loop que o…, summarize_order_chain(), traverse_order_chain_in_memory(), _store_com_pedidos() (+4 more)

### Community 22 - "Resiliência do supervisor"
Cohesion: 0.11
Nodes (17): degraded_reply(), _flag(), graceful_degradation(), guarded_tool(), Camada de resiliência da borda das tools e do supervisor. O gateway de LLM…, Fronteira de UMA tool: span, ponto de caos e (opt-in) circuit breaker., Resposta de degradação graciosa: um agente falhou, o turno termina com estado…, asyncio.wait_for com a semântica que o supervisor espera: cancela e devolve… (+9 more)

### Community 23 - "Calibração medida de limiares"
Cohesion: 0.10
Nodes (7): Calibração medida: escolha do limiar com erros, seleção de alvos (--only) e…, Categoria nova no conjunto de situações que o calibrador não conhece não entra…, aggregate() devolve o score que o teste atribuiu ao texto consultado., ScoredAtlas, test_every_scope_relevant_category_of_the_dataset_is_mapped_to_a_label(), test_overlap_is_not_written_without_allow_errors_but_is_with_it(), test_perfect_separation_suggests_midpoint_and_measures_the_brain_collection()

### Community 24 - "Consultas MongoDB do briefing"
Cohesion: 0.12
Nodes (19): Not LangGraph (hand-written orchestration), cache_autoembed_v1 index, cascade.py, $vectorSearch + $unionWith cascade, graph.py build_order_chain_pipeline, $graphLookup replacement chain, kb_lexical_v1 index, kb_autoembed_v1 index (+11 more)

### Community 25 - "Cascata semântica de cache"
Cohesion: 0.14
Nodes (18): cascade_long_term_context(), _cascade_lookup_fallback(), _cascade_lookup_raw(), cascade_store_short_term(), CascadeResult, is_compound_of(), looks_like_action_request(), DEMO_MODE não tem índice de vetor real — sem embedding local pra simular cosine… (+10 more)

### Community 26 - "Test Cache Isolation"
Cohesion: 0.16
Nodes (14): cascade_store_turn(), Grava sempre em curto_prazo e só promove respostas estáveis ao cache semântico.…, field_validator, Configuração central; segredos vêm somente do ambiente., Settings, test_atlas_index_drift_falls_back_without_breaking_the_turn(), test_cache_entry_from_previous_unrestricted_policy_is_ignored(), test_foreign_conversation_id_is_replaced_instead_of_hijacked() (+6 more)

### Community 27 - "API FastAPI"
Cohesion: 0.17
Nodes (19): agents(), decisions(), eval_runs(), get_metrics(), guardrails(), handoffs(), health(), inspector() (+11 more)

### Community 28 - "Orquestração do turno"
Cohesion: 0.21
Nodes (13): ChatResponse, TimelineEvent, _next_steps(), OrchestrationService, TurnBudget, Próximos passos do turno, sempre ancorados em documento existente. Falha aqui…, Uma linha: a chave do agente, `conversa` ou `nenhum`. Classificar é decisão,…, Pattern Parallel Fan-Out/Synthesis: agentes independentes rodam ao mesmo tempo… (+5 more)

### Community 29 - "Pov Agent Memory Mongodb Template"
Cohesion: 0.13
Nodes (20): Design: dark hero + JSON code card, three-column body, numbered benefit strip, Long-term Memory (episodic, semantic, procedural), Claim: Agent Memory e uma hierarquia de memorias, nao uma collection unica, Memory Engineering Stack (document model, automated embedding, Vector Search, Search+RRF, TTL, Change Streams), recall(): working -> cache -> long_term, vector + lexical + tenant filters, Shared Memory — camada transversal (ai_brain + multi_agent_poc), Short-term Memory (working memory + semantic cache), Slide: Uma plataforma de memoria — Agent Memory (template MongoDB) (+12 more)

### Community 30 - "Ataques fim-a-fim"
Cohesion: 0.22
Nodes (16): fact(), facts_of(), LLMGateway, parametrize, Ataques fim-a-fim (orquestrador real, DEMO_MODE, LLM roteirizado): memória…, Só o extrator responde (JSON roteirizado); demais agentes caem no template…, ScriptedLLM, test_episode_memory_cannot_carry_user_text_into_prompts() (+8 more)

### Community 31 - "Dependências do frontend"
Cohesion: 0.11
Nodes (18): dependencies, react, react-dom, vite, @vitejs/plugin-react, devDependencies, name, private (+10 more)

### Community 32 - "Calibração medida de limiares (2)"
Cohesion: 0.20
Nodes (17): ArgumentParser, apply_turn_threshold(), best_with_errors(), block_threshold_from(), build_parser(), calibrate(), denylist_filters(), main() (+9 more)

### Community 33 - "Injeção de falha"
Cohesion: 0.14
Nodes (15): _armed(), ChaosProviderError, enabled(), hook(), mangle(), Exception, Injeção de falha controlada — DESLIGADA salvo `CHAOS=1` no ambiente. O PoV…, Erro de provedor simulado; carrega `status_code` como o SDK real carrega. (+7 more)

### Community 34 - "DataStore e fronteira de tools"
Cohesion: 0.22
Nodes (7): _driver_session(), _matches(), Desembrulha o handle para o que o pymongo espera receber em `session=`., Live feed de handoffs do cliente: Change Stream no Atlas, poll no modo…, call_tool(), Executa UMA tool com span, ponto de caos, circuit breaker e (opt-in) teto de…, test_in_memory_store_matches_mongo_semantics_for_missing_fields()

### Community 35 - "Guia do repositório"
Cohesion: 0.13
Nodes (16): Escopo do PoV multiagente-atendimento, Orquestração manual em Python async (sem LangGraph), Portas estritas 8031 / 5191, agent_registry (config de agente como dado), Change Stream + SSE de eventos, cheap_route (roteamento determinístico), DataStore / DEMO_MODE, Fan-out paralelo order_agent + billing_agent (+8 more)

### Community 36 - "Regressão de caos"
Cohesion: 0.21
Nodes (15): _assert_scenario(), Regressão permanente dos cenários de caos (mesma implementação de…, test_concurrent_requests_on_one_conversation_do_not_corrupt_state(), test_failing_tool_opens_its_circuit(), test_hung_agent_is_interrupted_by_the_supervisor(), test_legacy_flag_restores_the_old_500_behaviour(), test_loop_guard_escalates_to_a_human(), test_malformed_tool_payload_never_invents_data() (+7 more)

### Community 37 - "Mapa de agentes"
Cohesion: 0.18
Nodes (15): ai_brain.agent_registry, billing_agent, kb_articles hybrid search, logistics_agent, loyalty_accounts collection, loyalty_agent, order_agent, product_agent (+7 more)

### Community 38 - "Troca de produto"
Cohesion: 0.21
Nodes (13): order_replacement_chain(), Cadeia de trocas do pedido, via $graphLookup no Atlas (loop em Python só em…, apply_replacement(), assess_replacement(), block_for_quality_review(), _chain_event(), Any, Troca de produto como operação de domínio — o único caminho que efetiva… (+5 more)

### Community 39 - "Escopo por embedding"
Cohesion: 0.19
Nodes (10): Atlas, parametrize, Classificador de escopo por embedding (in / out / chat): margem entre líder e…, where is my order?": os 12 vizinhos são todos `in`. `out` ausente = mais…, rows(), test_a_label_missing_among_the_neighbours_is_bounded_by_the_last_neighbour_not_treated_as_zero(), test_leader_must_beat_the_runner_up_by_its_own_margin(), test_query_uses_the_scope_index_in_the_brain_db_with_a_neighbourhood() (+2 more)

### Community 40 - "Test Concurrency"
Cohesion: 0.16
Nodes (9): API da PoV multi-agente., Settings, _validate_grove_url(), A mensagem chega ao classificador de escopo? Só quando NADA mais decidiu: sem…, reaches_scope_classifier(), Regressão do lost update: dois turnos concorrentes na MESMA conversation_id…, $set só deve mencionar active_order_id/active_invoice_id quando o turno de fato…, test_two_concurrent_turns_on_the_same_conversation_do_not_lose_a_turn() (+1 more)

### Community 41 - "Contratos de resposta"
Cohesion: 0.20
Nodes (12): update_agent(), AgentUpdate, ChatRequest, OrderStatusUpdate, Próximo passo clicável, sempre derivado de um documento que existe., Resolução de um caso escalado. `decision` é fechada: o analista escolhe entre…, ReviewResolution, Suggestion (+4 more)

### Community 42 - "Migrate Legacy Memory"
Cohesion: 0.30
Nodes (12): _fact_norm(), clear_legacy_price_cap(), main(), migrate(), Migra documentos legados de `customer_memory` (fact_type/value) para o formato…, Devolve quantos documentos legados foram (ou seriam) migrados., Remove o teto de R$ 350 que a migração anterior pôs nos fatos price_sensitive…, legacy_store() (+4 more)

### Community 43 - "Tracing por span"
Cohesion: 0.14
Nodes (9): active(), _NoSpan, Tracing distribuído opt-in, em cima de `tracing` do _shared (pov-shared 0.1.4).…, Liga o tracing conforme TRACE_SINK. Fail-open: erro aqui nunca impede o app de…, Span com latência medida. Vira um no-op quando o tracing está desligado., Tokens e custo estimado de UMA chamada, no span dela., record_llm_usage(), setup_tracing() (+1 more)

### Community 44 - "Escopo por embedding (2)"
Cohesion: 0.21
Nodes (13): best_scores(), classify(), decide(), DataStore, Classificador de ESCOPO — "esta mensagem é assunto da loja?" — feito no…, Regra pura (testável sem Atlas). Devolve (escopo, margem do líder sobre o…, Melhor score por rótulo entre os vizinhos, ou None se não deu para consultar…, Devolve {scope: in|out|chat|unsure, margin, in_score, out_score, chat_score,… (+5 more)

### Community 45 - "Adr 004 Escopo Por Embedding E Medicao P"
Cohesion: 0.16
Nodes (14): ADR-002 LLM memory and personal turn, ADR-003 two-band guardrail, Ambiguous band goes to LLM (unsure), Baseline before ADR-004 (n=229), `conversa` exit, ADR-004 decision (scope by embedding), Dev/holdout split by message hash, eval_situations.py (+6 more)

### Community 46 - "Seed e índices Atlas"
Cohesion: 0.26
Nodes (9): seed_documents(), main(), Restaura os saldos que a própria demo/eval consome (idempotente, só as contas…, restore(), create_search_indexes(), main(), Seed idempotente do plano de dados e do plano de coordenação., seed() (+1 more)

### Community 47 - "Atritos com o _shared"
Cohesion: 0.15
Nodes (13): build_turn_trace (Langfuse, uma trace por turno), Nunca mencionar Postgres em material de cliente, Bugs reais revelados pela bateria, app/resilience.py:call_tool (fronteira única de tool), app/llm.py (gateway Anthropic com retry/breaker), app/observability.py (contorno do init_tracing), Convenção contra colisão de nomes de módulo, Extra `tracing` do _shared (+5 more)

### Community 48 - "Adr 001 Arquitetura Multi Agente"
Cohesion: 0.18
Nodes (13): ADR-001 Coordenacao multi-agente orientada a documentos, ADR-002 Memoria LLM e turno pessoal, ADR-003 Guardrail em duas faixas, ADR-004 Escopo por embedding e medicao, agent_conversations, ai_brain.agent_registry, Parallel fan-out order + billing, agent_handoffs / agent_traces (+5 more)

### Community 49 - "Mapa de agentes (2)"
Cohesion: 0.17
Nodes (12): cheap_route (router.py), orchestrator, Pendencias conhecidas, reaches_scope_classifier, ROUTER_PROMPT, scope_classifier.py (in/out/chat), scope_probes collection (214), scope_probes_vs index (+4 more)

### Community 50 - "Golden eval"
Cohesion: 0.24
Nodes (8): Estimated LLM cost from provider usage; absent tariffs are never zero cost., summarize_evals(), grade_case(), grade_outcome(), main(), Eval harness: roda o golden dataset (app/seed_data.py:EVAL_CASES) contra o…, run(), snapshot()

### Community 51 - "Trace do turno (Langfuse)"
Cohesion: 0.21
Nodes (6): build_turn_trace(), get_langfuse(), _NoopLangfuse, _NoopTrace, Sem chave configurada (ou Langfuse fora do ar): instrumentação vira no-op,…, Uma trace por turno cobrindo a timeline INTEIRA — roteamento, decisão de cache,…

### Community 52 - "Busca híbrida e vetorial"
Cohesion: 0.26
Nodes (10): build_kb_lexical_pipeline(), build_kb_rank_fusion_pipeline(), build_kb_vector_pipeline(), Combina rankings lexical e vetorial sem comparar escalas de score. Continua…, Perna semântica: Atlas Vector Search com Automated Embedding (voyage-4)., Perna lexical: BM25 com boost no título (analyzer português)., Híbrido server-side: $rankFusion funde as duas pernas dentro do banco (MongoDB…, reciprocal_rank_fusion() (+2 more)

### Community 53 - "JWT e mascaramento"
Cohesion: 0.18
Nodes (10): current_customer(), issue_token(), Depends, Request, request_identity_key(), require_admin(), secrets_equal(), bearer (+2 more)

### Community 54 - "Eval de roteamento"
Cohesion: 0.29
Nodes (11): _customers(), _expected(), main(), Eval de roteamento multiagente: acurácia de rota, taxa de resolução e handoffs…, Agente de ENTRADA do turno — roteamento é a primeira decisão, não o fim da…, Fan-out não tem ordem: o esperado é o CONJUNTO de agentes disparados em…, Resolvido = o turno entregou o desfecho esperado, sem degradar e sem cair no…, report() (+3 more)

### Community 55 - "Adr 004 Escopo Por Embedding E Medicao P (2)"
Cohesion: 0.20
Nodes (12): calibrate_thresholds.py --only scope, router.DOMAIN_VOCAB word list (ADR-003), Margin-based decision rule, Missing-label bounded by last neighbour, No-verdict fallback to word list, orchestration.reaches_scope_classifier, Async reindex on adding probes, scope_classifier.py (+4 more)

### Community 56 - "API FastAPI (2)"
Cohesion: 0.22
Nodes (11): set_store(), budget_handler(), lifespan(), log(), Exception, request_context(), unhandled_error_handler(), exception_handler (+3 more)

### Community 57 - "Test Cache Eligibility"
Cohesion: 0.36
Nodes (10): utcnow(), Cache útil E seguro: memória estruturada do cliente não bloqueia pergunta…, O cache global guarda a resposta SEM orçamento; servi-la a quem tem teto…, test_customer_with_budget_never_receives_the_generic_cached_recommendation(), test_generic_answer_is_cached_even_for_customer_with_facts_and_history(), test_global_cache_serves_other_customers_the_generic_answer(), test_only_structured_episodes_reach_the_prompt(), test_turn_that_used_the_budget_is_never_cached() (+2 more)

### Community 58 - "API FastAPI (3)"
Cohesion: 0.24
Nodes (11): chat(), _degraded_turn(), demo_reset(), demo_scenarios(), events_stream(), Degradação graciosa no topo: o turno falhou, mas o cliente recebe estado…, Desfaz o que a demo gravou NESTE cliente (customer_key do JWT, nunca do corpo)…, Roteiro versionado no plano de coordenação; UI, warmup e eval usam a mesma… (+3 more)

### Community 59 - "Test Live Stream"
Cohesion: 0.29
Nodes (7): handoff_event_stream(), Adapt the Change Stream to SSE with immediate confirmation and heartbeats., ConnectedRequest, IdleStore, OneHandoffStore, test_sse_confirms_connection_before_first_handoff_and_then_emits_data(), test_sse_sends_heartbeat_while_change_stream_is_idle()

### Community 60 - "Eval por situações"
Cohesion: 0.25
Nodes (9): compare(), main(), outcome_of(), Mede o agente REAL (Atlas + LLM) contra tests/data/situations.json — o que um…, O que o cliente viu: bloqueado, orientação de escopo, boas-vindas ou qual…, Taxas que importam ao cliente, separadas de acerto de rótulo., report(), run() (+1 more)

### Community 61 - "Guia do repositório (2)"
Cohesion: 0.25
Nodes (11): Estado que vive no cluster Atlas (fora do git), calibrate_thresholds.py (limiares medidos), Denylist semântica auto-alimentada, Guardrail vetorial de duas faixas, Hook pre-push (ruff + offline + LIVE), scope_classifier (escopo por embedding), turn_classifier (elegibilidade de cache por vetor), Scope by embedding (ADR-004) (+3 more)

### Community 62 - "Relatório de caos"
Cohesion: 0.22
Nodes (11): app/chaos.py (injeção no caminho real), Cenário agent_hang, Cenário crash_resume (SIGKILL, Atlas real), Cenário legacy_500_flag, Cenário loop_guard, Cenário tool_timeout, chaos_suite.py (bateria de caos 11/11), Tabela de flags opt-in (+3 more)

### Community 63 - "Grove Costs 2026 09 18"
Cohesion: 0.20
Nodes (11): Claude Haiku 4.5 (Anthropic) - $1.41, 25.2% of cost, Claude Opus 4.8 (Anthropic) - $0.18, 3.2% of cost, Claude Opus 5 (Anthropic) - $0.0015, 0.0% of cost, Claude Sonnet 4.5 (Anthropic) - $1.24, 22.2% of cost, Claude Sonnet 4.6 (Anthropic) - $2.09, 37.3% of cost, Claude Sonnet 5 (Anthropic) - $0.65, 11.7% of cost, GitHub Copilot (usage source), GPT-5.3 Codex (OpenAI) - $0.02, 0.4% of cost (+3 more)

### Community 64 - "Gateway de LLM"
Cohesion: 0.20
Nodes (4): _CircuitBreaker, TurnBudget, False quando o circuito está aberto e ainda dentro da janela de curto-circuito., BudgetExceeded

### Community 65 - "Baseline de testes"
Cohesion: 0.27
Nodes (10): Memória do cliente extraída por LLM, MEMORY_DEMOS (chips de demo das camadas de memória), Cascata semântica (curto prazo -> cache global), Warmup automático do cache semântico, Baseline da suíte offline (commit f279bfc), tests/test_auto_warmup.py, tests/test_budget_policy.py, tests/test_cache_isolation.py (+2 more)

### Community 66 - "Adr 004 Escopo Por Embedding E Medicao P (3)"
Cohesion: 0.20
Nodes (10): Set growth to 287, generate_situations.py (--append), Out-of-scope orientation (0 tokens), Precision-first thresholds, floor 0.04, Outlier 'o roteador que adquiri nao conecta', Routing LLM before security (ambiguous, no suspicion), Small samples, Second round: pending items done (+2 more)

### Community 67 - "Comportamento dos agentes (briefing)"
Cohesion: 0.20
Nodes (9): agent_conversations, agent_handoffs, agent_traces, Manual checkpointing collections, short_term_memory (24h), turn_classifier (turn_probes, 0.7162), Collections in action panel, Memory/cache demo chips (+1 more)

### Community 68 - "Mapa de agentes (3)"
Cohesion: 0.22
Nodes (9): ADR-001 multi-agent architecture, ADR-002 LLM memory and personal turn, ADR-003 two-band guardrail and out-of-scope, ADR-004 scope by embedding + situations, eval_situations.py, generate_situations.py (--append), looks_like_instruction filter, LLM memory extractor (memory.py) (+1 more)

### Community 69 - "Resiliência do supervisor (2)"
Cohesion: 0.22
Nodes (7): Estado do supervisor para ESTE turno: teto de passos, timeout e detector de…, _supervisor_state(), agent_timeout_seconds(), loop_guard_repeats(), LoopGuard, Detecta o supervisor girando: MESMO agente com a MESMA intenção repetidas…, True quando esta visita estoura o limite (o chamador encerra a cadeia).

### Community 70 - "Test Live Random"
Cohesion: 0.22
Nodes (3): live(), fixture, Bateria LIVE de perguntas ALEATÓRIAS (Atlas + LLM reais): cd backend && LIVE=1…

### Community 71 - "Adr 004 Escopo Por Embedding E Medicao P (4)"
Cohesion: 0.25
Nodes (8): LLM security classifier + self-reinforcing write-back, guardrails.needs_security_review, Modelo de segurança por customer_key do JWT, customer_key isolation safety net, guardrails.needs_security_review, Security before agent outside keyword route, Security classifier prompt update, Fronteira de produção (fail-closed na inicialização)

### Community 72 - "Agentes especializados (2)"
Cohesion: 0.25
Nodes (8): detect_category(), _local_rank(), Relevância pesa mais, mas nota e disponibilidade desempatam — igual a um…, Singular/plural aproximado em pt-BR: 'fones' e 'fone' precisam casar na busca…, Devolve (artigos, estratégia). A estratégia vira o título do evento de timeline…, search_kb(), _stem(), _weighted_score()

### Community 73 - "Guardrails de borda"
Cohesion: 0.38
Nodes (6): enabled(), mask_log(), Guardrails de BORDA usando o pacote comum (`guardrails` do _shared), opt-in por…, Mascara PII em todo valor de texto de um evento de log., Valida a resposta serializada contra o próprio schema. Nunca derruba o turno., validate_response()

### Community 74 - "API FastAPI (4)"
Cohesion: 0.29
Nodes (7): approve_candidate(), create_token(), Aquece o cache em segundo plano e responde na hora. Aberto de propósito (a UI…, Fecha a pausa: grava a decisão humana (imutável) e devolve o caso ao agente. O…, resolve_pending_review(), warmup(), post

### Community 75 - "Test Security Config"
Cohesion: 0.48
Nodes (6): Fail startup on configurations that would expose demo credentials., validate_runtime_security(), production_settings(), parametrize, test_insecure_production_configuration_is_rejected(), test_secure_production_configuration_is_accepted()

### Community 77 - "Probes de escopo"
Cohesion: 0.48
Nodes (6): create_index(), main(), DataStore, Semeia SÓ o classificador de escopo (probes rotulados in/out/chat + índice…, Upsert dos probes em <brain_db>.scope_probes. Devolve quantos são novos., seed_probes()

### Community 78 - "Formato do eval"
Cohesion: 0.29
Nodes (7): situations.json (287 situações, dev/holdout), eval_situations.py / generate_situations.py, Limitações conhecidas do relatório de caos, Comparação multiagente x singleagent, backend/eval_routing.py, eval/routing_dataset.json (24 casos sintéticos), synthetic: true + campo limitation

### Community 79 - "Adr 002 Memoria Llm E Turno Pessoal"
Cohesion: 0.29
Nodes (7): ADR-002 Memória por LLM e turno pessoal, Budget pre-filter (max_price_brl in $vectorSearch), Long-term episode memory (system labels only), looks_like_instruction, LLM memory extractor with supersession, Personal-turn gates and turn classifier, Semantic cache cascade (short-term/session/customer/global)

### Community 80 - "Agent Quality Economics"
Cohesion: 0.29
Nodes (7): claude-haiku-4-5 model, eval.py avaliador, eval_runs collection, gpt-5.6-luna model, grove-mixed-live eval run, bruno-paraphrase-exfiltration eval case, ana-paraphrase-jailbreak eval case

### Community 81 - "Mapa de agentes (4)"
Cohesion: 0.33
Nodes (6): calibrate_thresholds.py, scope_classifier_config, seed_turn_probes.py, turn_classifier (threshold 0.7162), vector_block_threshold = 0.8814, vector_threshold

### Community 82 - "Mapa de agentes (5)"
Cohesion: 0.33
Nodes (6): DEMO_MODE in-memory DataStore, denylist_autoembed_v1 semantic denylist, GROUNDING_RULES, llm_synthesize grounded responses, overlap_score (Jaccard), Static denylist + near-miss

### Community 83 - "Smoke caixa-preta"
Cohesion: 0.47
Nodes (5): check(), main(), Client, Smoke test contra a API no ar. Uso: python tests/smoke.py [URL]., token()

### Community 84 - "Guia do repositório (3)"
Cohesion: 0.33
Nodes (5): Architecture, Commands, Continuidade da revisão de resiliência, Known gaps (verified against code, not just docs), Project

### Community 85 - "Agent Quality Economics (2)"
Cohesion: 0.40
Nodes (6): Grove Gateway, llm_calls ledger, LLM_PRICES config, Fórmula de custo por chamada (tarifas separadas), Fórmula de estimativa por média histórica, Grove Gateway captured costs table

### Community 86 - "Mapa de agentes (6)"
Cohesion: 0.40
Nodes (4): Architecture, Commands, Known gaps (verified against code, not just docs), Project

### Community 87 - "Contratos de resposta (2)"
Cohesion: 0.50
Nodes (4): Any, _jsonable(), Tipos do driver (ObjectId, Decimal128, bytes) viram texto: documentos reais do…, field_serializer

### Community 88 - "DataStore e fronteira de tools (2)"
Cohesion: 0.40
Nodes (3): Escrita de negócio e registro de decisão como uma coisa só. O problema que isto…, Handle de uma transação em curso. `driver_session` é a sessão do pymongo, ou…, Transaction

### Community 89 - "Adr 003 Guardrail Em Duas Faixas"
Cohesion: 0.40
Nodes (5): ADR-002 Memoria LLM e turno pessoal, ADR-003 Guardrail em duas faixas e fora de escopo, ADR-003 discarded alternatives, Domain vocabulary (DOMAIN_VOCAB / has_domain_signal), Out-of-scope handling (deterministic)

### Community 90 - "Mcp"
Cohesion: 0.40
Nodes (4): MDB_MCP_CONNECTION_STRING, npx, mongodb, mongodb-mcp-server

### Community 91 - "DataStore e fronteira de tools (3)"
Cohesion: 0.50
Nodes (3): get_store(), Só para pipelines reais ($vectorSearch/$unionWith) — sem equivalente em…, RuntimeError

### Community 93 - "Slide Docs Brief"
Cohesion: 0.50
Nodes (3): ADR-001-arquitetura-multi-agente.md, Documentação dividida por leitor, Documentação faltante (RUNBOOK, data-model, ADR-002+, SECURITY.md)

### Community 94 - "Grove Costs 2026 09 19"
Cohesion: 0.67
Nodes (4): Claude Haiku 4.5 (Anthropic) usage row, GPT-5.6 Luna (OpenAI) usage row, Usage by Model cost table (Grove gateway dashboard), Grove gateway (Anthropic APIM) — PoV LLM access layer

### Community 96 - "Mapa de agentes (7)"
Cohesion: 0.67
Nodes (3): Known gaps, Langfuse build_turn_trace, SSE + Change Stream + op counters

### Community 99 - "Grove Cost Guide"
Cohesion: 0.67
Nodes (3): LLM_BLENDED_PRICES config, Premissa histórica 18/09/2026 (substituída), Regra vigente 19/09/2026 (LLM_BLENDED_PRICES)

### Community 101 - "Ci"
Cohesion: 0.67
Nodes (3): Backend tests and lint job, CI Workflow, Frontend build job

## Ambiguous Edges - Review These
- `MODO ADMIN toggle gating per-agent enable/disable switches` → `Principle: input validated once per turn, before any model, memory or trace`  [AMBIGUOUS]
  docs/screenshots/04-agents-registry.png · relation: conceptually_related_to
- `GPT-5.3 Codex (OpenAI) - $0.02, 0.4% of cost` → `Grove Gateway (usage source)`  [AMBIGUOUS]
  docs/internal/assets/grove-costs-2026-09-18.png · relation: shares_data_with

## Knowledge Gaps
- **189 isolated node(s):** `devDependencies`, `name`, `private`, `build`, `dev` (+184 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 648 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **60 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `MODO ADMIN toggle gating per-agent enable/disable switches` and `Principle: input validated once per turn, before any model, memory or trace`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `GPT-5.3 Codex (OpenAI) - $0.02, 0.4% of cost` and `Grove Gateway (usage source)`?**
  _Edge tagged AMBIGUOUS (relation: shares_data_with) - confidence is low._
- **Why does `DataStore` connect `Trilha de decisões` to `Memória do cliente (LLM)`, `Fora de escopo e saudação`, `Isolamento de banco de teste`, `Bateria de caos`, `Guardrail de entrada e saída`, `Turno pessoal fora do cache`, `Agentes especializados`, `Orçamento do cliente no catálogo`, `Respostas de orientação`, `Fila de revisão humana`, `Classificador de turno pessoal`, `Warmup do cache`, `Economia do gateway de LLM`, `Test Live`, `Cascata semântica de cache`, `Test Cache Isolation`, `API FastAPI`, `Orquestração do turno`, `Ataques fim-a-fim`, `Injeção de falha`, `DataStore e fronteira de tools`, `Troca de produto`, `Test Concurrency`, `Contratos de resposta`, `Migrate Legacy Memory`, `Seed e índices Atlas`, `JWT e mascaramento`, `Eval de roteamento`, `API FastAPI (2)`, `Test Cache Eligibility`, `API FastAPI (3)`, `Test Live Stream`, `Test Live Random`, `Agentes especializados (2)`, `API FastAPI (4)`, `DataStore e fronteira de tools (2)`, `DataStore e fronteira de tools (3)`, `Test Concurrency (2)`, `Test Concurrency (3)`, `Test Fuzz Memory`?**
  _High betweenness centrality (0.151) - this node is a cross-community bridge._
- **Why does `OrchestrationService` connect `Orquestração do turno` to `Memória do cliente (LLM)`, `Fora de escopo e saudação`, `Bateria de caos`, `Test Live Random`, `Escopo integrado ao turno`, `Test Concurrency`, `Trilha de decisões`, `Golden eval`, `Economia do gateway de LLM`, `Test Live`, `Eval de roteamento`, `API FastAPI (2)`, `Test Cache Eligibility`, `Test Cache Isolation`, `API FastAPI`, `Eval por situações`, `Ataques fim-a-fim`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Why does `Settings` connect `Test Cache Isolation` to `Memória do cliente (LLM)`, `Fora de escopo e saudação`, `Guardrail de entrada e saída`, `Turno pessoal fora do cache`, `Trilha de decisões`, `Orçamento do cliente no catálogo`, `Fila de revisão humana`, `Classificador de turno pessoal`, `Warmup do cache`, `Test Live`, `Ataques fim-a-fim`, `Test Concurrency`, `Migrate Legacy Memory`, `Seed e índices Atlas`, `Golden eval`, `Trace do turno (Langfuse)`, `JWT e mascaramento`, `Test Cache Eligibility`, `Test Security Config`, `Test Concurrency (2)`, `Test Concurrency (3)`, `Test Fuzz Memory`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Are the 67 inferred relationships involving `DataStore` (e.g. with `order_replacement_chain()` and `run_billing_agent()`) actually correct?**
  _`DataStore` has 67 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `Settings` (e.g. with `build_turn_trace()` and `get_langfuse()`) actually correct?**
  _`Settings` has 6 INFERRED edges - model-reasoned connections that need verification._