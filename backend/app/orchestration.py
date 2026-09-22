import asyncio
import uuid
from time import perf_counter

from .agents import RUNNERS
from .economics import summarize_calls
from .budget import BudgetExceeded, TurnBudget, estimate_tokens
from .cascade import (GLOBAL_CACHE_INTENTS, CascadeResult, cascade_long_term_context, cascade_lookup, cascade_store_episode,
                      cascade_store_short_term, cascade_store_turn)
from .database import DataStore, utcnow
from . import chaos, observability, resilience, scope_classifier
from .guardrails import check_input, check_output, needs_security_review
from .langfuse_client import build_turn_trace
from .llm import LLMGateway
from .memory import active_budget, extract_and_store, looks_like_instruction
from .metrics import metrics
from .models import ChatResponse, TimelineEvent
from .router import (RouteDecision, cheap_route, deterministic_orchestrator, detect_fanout, has_domain_signal,
                     has_weak_signal, has_catalog_anchor, out_of_scope_sentences)
from .guidance import (blocked_reply, build_suggestions, customer_snapshot, greeting_reply,
                       is_capabilities_question, is_greeting, is_meta_question, is_thanks, looks_like_own_pii, meta_reply,
                       out_of_scope_reply, pii_block_reply, thanks_reply)
from .security import mask_pii


ROUTER_PROMPT = (
    "Classifique a intenção do cliente e escolha o agente certo. Responda com UMA linha, só a chave, sem explicação.\n"
    "order_agent: status, rastreio, cancelamento, troca, devolução ou reembolso de um PEDIDO já feito, e pedido para ver o "
    "histórico de compras ou os dados cadastrais do PRÓPRIO cliente.\n"
    "product_agent: recomendação/comparação de PRODUTOS do catálogo (fones, monitores, teclados, mouses, carregadores, "
    "smartwatches etc.), preço e disponibilidade, mesmo sem usar a palavra 'produto'.\n"
    "support_agent: problema técnico/defeito num produto que o cliente TEM (de qualquer tipo, mesmo que a loja não o venda), "
    "e pedido para falar com atendente humano ou abrir chamado.\n"
    "billing_agent: fatura, cobrança, valor a pagar, vencimento, nota fiscal, contestação de cobrança.\n"
    "warranty_agent: garantia — se um produto está coberto, prazo, o que a garantia cobre.\n"
    "loyalty_agent: pontos, nível de fidelidade, resgate de pontos.\n"
    "logistics_agent: transportadora, previsão de entrega, código de rastreamento, reagendar entrega.\n"
    "conversa: SOMENTE cumprimento, agradecimento, despedida ou pergunta sobre quem é o assistente e o que ele faz. Pedido de poema, "
    "piada, receita, ou informação da loja (CNPJ, endereço, horário) NÃO é conversa: é 'nenhum'.\n"
    "nenhum: a mensagem não é sobre atendimento desta loja (assunto aleatório, teste, texto sem sentido) — responda exatamente "
    "'nenhum' nesse caso, NUNCA escolha um agente por eliminação.\n"
    "Chaves permitidas: "
)


def _supervisor_state(conversation_id: str) -> dict:
    """Estado do supervisor para ESTE turno: teto de passos, timeout e detector de loop."""
    return {"strict": resilience.supervisor_strict(),
            "guard": resilience.LoopGuard(),
            "timeout": resilience.agent_timeout_seconds(),
            "conversation_id": conversation_id}


def reaches_scope_classifier(message: str) -> bool:
    """A mensagem chega ao classificador de escopo? Só quando NADA mais decidiu: sem palavra forte, sem rota determinística e sem
    ser saudação/agradecimento/meta óbvios. A calibração mede exatamente esta população — não itens que nunca chegariam a ele."""
    return (not has_domain_signal(message) and deterministic_orchestrator(message).source == "fallback"
            and not (is_greeting(message) or is_thanks(message) or is_meta_question(message) or is_capabilities_question(message)))


async def _record_collection_metrics(timeline: list[TimelineEvent]) -> None:
    """Contador cumulativo de toque por collection+operação — alimenta o painel 'Coleções' no front,
    prova visual de que MongoDB é o único data store por trás de leitura, escrita, vector e hybrid search."""
    for event in timeline:
        if event.collection and event.op and not event.replayed:
            await metrics.increment(f"collection.{event.collection}.{event.op}")


MAX_HOPS = 5
# Retornos só existem quando representam uma dependência de negócio explícita. O limite por agente
# mantém o grafo finito mesmo se uma configuração dinâmica introduzir um ciclo acidental.
ALLOWED_REVISITS = {("logistics_agent", "order_agent")}
MAX_VISITS_PER_AGENT = 2
FALLBACK_AGENTS = {
    "product_agent": "support_agent",
    "support_agent": "order_agent",
    "billing_agent": "order_agent",
    "order_agent": "support_agent",
    "warranty_agent": "support_agent",
    "loyalty_agent": "order_agent",
    "logistics_agent": "order_agent",
}


# Agentes cujo runner pode escrever (resgate, mudança de status, reagendamento, chamado). O registry
# inteiro é montado uma única vez no início de run_turn; se um destes for desativado via
# PATCH /api/admin/agents enquanto um turno com handoffs em cadeia já está em andamento, a versão em
# memória carregada no início não vê a mudança. Para estes agentes, uma checagem extra direto no
# banco roda imediatamente antes de cada runner() no loop de handoff — os agentes só de leitura
# seguem confiando no registry do início do turno, que é onde o custo da consulta extra compensa.
WRITE_EFFECT_AGENTS = {"loyalty_agent", "order_agent", "logistics_agent", "support_agent"}


TOPIC_BY_AGENT = {
    # Tema que cada agente já cobriu no turno: sugerir de volta exatamente o que o
    # cliente acabou de perguntar é pior que não sugerir nada.
    "order_agent": "order",
    "billing_agent": "invoice",
    "logistics_agent": "shipment",
    "loyalty_agent": "loyalty",
    "product_agent": "product",
    "warranty_agent": "order",
}


async def _next_steps(store, customer: dict, *, covered: set[str]) -> list[dict]:
    """Próximos passos do turno, sempre ancorados em documento existente.

    Falha aqui nunca derruba a resposta que já foi produzida — a lista some e o
    turno segue normal.
    """
    try:
        snapshot = await customer_snapshot(store, customer)
        return build_suggestions(snapshot, exclude=covered)
    except Exception:  # noqa: BLE001 — enfeite útil, nunca caminho crítico
        return []


class OrchestrationService:
    def __init__(self, store: DataStore, llm: LLMGateway, global_budget: int):
        self.store = store
        self.llm = llm
        self.global_budget = global_budget

    async def _route_with_llm(self, message: str, orchestrator: dict, allowed: list[str], budget) -> str | None:
        """Uma linha: a chave do agente, `conversa` ou `nenhum`. Classificar é decisão, não criação: temperature 0."""
        with observability.span("routing", **{"routing.candidates": len(allowed)}) as current:
            text, _ = await self.llm.complete(
                agent={**orchestrator, "temperature": 0}, user_message=message,
                dynamic_context=ROUTER_PROMPT + ", ".join(allowed) + ", conversa, nenhum", budget=budget)
            current.set_attribute("routing.decision", (text or "").strip().splitlines()[0][:40] if text else "sem_resposta")
        return text

    @staticmethod
    def _usage(budget):
        return {**budget.used_by_agent, "total": budget.total_used,
                "cache_read": budget.cache_read_tokens, "cache_write": budget.cache_write_tokens}

    @staticmethod
    def _response(budget, **kwargs):
        return ChatResponse(**kwargs, llm_calls=budget.llm_calls, economics=summarize_calls(budget.llm_calls))

    async def run_turn(self, message: str, customer: dict, conversation_id: str | None) -> ChatResponse:
        started = perf_counter()
        requested_conversation_id = conversation_id
        conversation_id = requested_conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
        masked = mask_pii(message)
        timeline: list[TimelineEvent] = []

        agents, rules, memory, conversation = await asyncio.gather(
            self.store.find_many("agent_registry", {"active": True}, brain=True, limit=20),
            self.store.find_many("routing_rules", {}, brain=True, limit=100),
            self.store.find_many("customer_memory", {"customer_key": customer["customer_key"], "active": True}, limit=5),
            self.store.find_one("agent_conversations", {"conversation_id": conversation_id, "customer_key": customer["customer_key"]}),
        )
        # Um ID fornecido só pode retomar uma conversa que pertence ao JWT atual. IDs desconhecidos ou de
        # outro cliente viram uma conversa nova; isso evita leitura de cache e overwrite por ID adivinhado.
        if requested_conversation_id and conversation is None:
            conversation_id = f"conv-{uuid.uuid4().hex[:12]}"
        registry = {agent["agent_key"]: agent for agent in agents}
        per_agent = {key: int(value["max_turn_tokens"]) for key, value in registry.items()}
        budget = TurnBudget(self.global_budget, per_agent)

        quick_decision = cheap_route(masked, rules)
        # Escopo por EMBEDDING antes de gastar LLM: a lista de palavras escorrega (inglês, gíria, erro de digitação, assunto que ninguém
        # previu). Só consulta quando nenhuma regra nem palavra forte decidiu e a mensagem não é saudação/agradecimento/meta óbvia. Sem
        # veredito REAL (DEMO_MODE, índice ausente, limiar não medido, erro) volta ao comportamento anterior, por palavras.
        scope_verdict = None
        # rota de produto apoiada só no verbo genérico "recomenda" (regra seedada): o escopo pode recusá-la se for decisivo
        weak_product_route = (quick_decision is not None and quick_decision.target_agent == "product_agent"
                              and not has_catalog_anchor(masked))
        if (quick_decision is None and reaches_scope_classifier(masked)) or weak_product_route:
            try:
                scope_verdict = await scope_classifier.classify(self.store, masked)
            except Exception:  # noqa: BLE001 — classificador de escopo nunca derruba o turno
                scope_verdict = None
            if scope_verdict is not None and (scope_verdict.get("method") != "vector" or scope_verdict.get("error")):
                scope_verdict = None
        # Mensagem sem NENHUM sinal de domínio vai virar a orientação enlatada, sem agente e sem LLM: pagar o classificador de segurança
        # (~300 tokens) para proteger uma resposta fixa não compra nada. As camadas grátis (denylist lexical + vetorial) continuam; o
        # classificador fica para o que pode chegar a um agente. Com veredito de escopo real, ele manda; sem, valem as palavras.
        if scope_verdict is not None:
            no_domain_signal = scope_verdict["scope"] in ("out", "chat")
        else:
            no_domain_signal = (quick_decision is None and not has_domain_signal(masked) and not has_weak_signal(masked)
                                and deterministic_orchestrator(masked).source == "fallback")
        # forma de exfiltração/autoridade/injeção embrulhada em qualquer coisa ainda merece o classificador (é ele que marca como ataque)
        suspicious = looks_like_instruction(masked) or needs_security_review(masked)
        # Faixa ambígua sem suspeita: o roteamento vem ANTES da segurança. Se ele concluir `nenhum`/`conversa`, a resposta é enlatada e o
        # classificador de segurança (~370 tokens) não compra nada; se escolher um agente, a segurança roda logo em seguida, como sempre.
        pre_route, canned_route = None, False
        orchestrator_doc = registry.get("orchestrator")
        if (scope_verdict is not None and scope_verdict["scope"] == "unsure" and quick_decision is None and not suspicious
                and not has_domain_signal(masked) and orchestrator_doc and self.llm.client):
            pre_route = await self._route_with_llm(masked, orchestrator_doc, [key for key in RUNNERS if key in registry], budget)
            canned_route = (pre_route or "").strip().lower().startswith(("nenhum", "conversa"))
        skip_guardrail_llm = (quick_decision is not None or no_domain_signal or canned_route) and not suspicious
        guardrail = await check_input(self.store, masked, customer, llm=self.llm, budget=budget, agent_doc=registry.get("orchestrator"), skip_semantic=skip_guardrail_llm)
        guardrail_title = "Guardrail de entrada"
        if guardrail.blocked and guardrail.reason == "semantic_llm":
            guardrail_title += " (classificado pelo modelo)"
        elif guardrail.uncertain:
            guardrail_title += " (dúvida do modelo — abstenção, seguiu com o turno, fila de revisão)"
        timeline.append(TimelineEvent(category="guardrail", title=guardrail_title, collection="guardrail_denylist", op="read", filter={"area": customer["area"]}, result={"blocked": guardrail.blocked, "score": guardrail.score, "reason": guardrail.reason, "uncertain": guardrail.uncertain}))
        if guardrail.blocked:
            await metrics.increment("guardrails.blocked")
            # O bloqueio continua sendo bloqueio — o texto não amolece nem negocia. O que muda é
            # que a conversa não termina num muro: quem testou o limite de propósito vê o limite
            # funcionando E o caminho de volta, com dados reais desta identidade.
            snapshot = await customer_snapshot(self.store, customer)
            response = (
                pii_block_reply(snapshot) if looks_like_own_pii(masked)
                else blocked_reply(
                    snapshot,
                    base="Não posso atender essa solicitação porque ela viola a política de segurança.",
                )
            )
            trace_url = await self._persist_trace(conversation_id, customer, masked, response, timeline, "guardrail", self._usage(budget), (perf_counter() - started) * 1000, llm_calls=budget.llm_calls)
            await _record_collection_metrics(timeline)
            return self._response(budget, conversation_id=conversation_id, response=response, active_agent="guardrail", route_source="fallback", cache_hit=False, timeline=timeline, usage=self._usage(budget), suggestions=build_suggestions(snapshot), langfuse_trace_url=trace_url)

        written_facts = await extract_and_store(self.store, customer["customer_key"], masked, llm=self.llm, budget=budget, agent_doc=registry.get("orchestrator"))
        if written_facts:
            timeline.append(TimelineEvent(category="memory", title="Fato extraído do turno e persistido (LLM + supersessão)", collection="customer_memory", op="write", filter={"customer_key": customer["customer_key"]}, result=written_facts))

        fanout_targets = detect_fanout(masked, rules)
        if fanout_targets and all(target in registry for target in fanout_targets):
            return await self._run_fanout(fanout_targets, masked, customer, registry, budget, conversation_id, conversation, timeline, started)

        decision = quick_decision
        scope_reason, chat_verdict = None, False
        if weak_product_route and scope_verdict is not None and scope_verdict["scope"] == "out":
            decision = RouteDecision("fora_de_escopo", None, "fallback", 0.0)
            scope_reason = "classificador_de_escopo"
        if decision is None:
            decision = deterministic_orchestrator(masked)
            orchestrator = registry.get("orchestrator")
            # só consulta o LLM quando o determinístico não achou palavra-chave alguma (fallback puro, 0.55) —
            # se já identificou defeito/produto/fatura com confiança, essa decisão é mais estável que uma
            # classificação de LLM e não deve ser sobrescrita por variação de amostragem do modelo.
            llm_ok = bool(orchestrator and self.llm.client)
            if decision.source == "fallback" and not has_domain_signal(masked):
                if scope_verdict is not None:
                    # veredito real do embedding: out/chat resolvem sozinhos (0 tokens); in/unsure precisam do LLM para escolher o
                    # agente (ou dizer "nenhum") — sem LLM, "in" cai no agente padrão e a dúvida vira orientação, nunca palpite
                    refuse = scope_verdict["scope"] in ("out", "chat") or (scope_verdict["scope"] == "unsure" and not llm_ok)
                    reason = "classificador_de_escopo"
                    chat_verdict = scope_verdict["scope"] == "chat"
                else:
                    # Nenhum sinal FORTE do domínio e, se só há palavras genéricas, nem classificador para decidir: não vale pagar
                    # (nem adivinhar order_agent). A orientação é determinística e vale também sem LLM (DEMO_MODE/CI).
                    refuse = not (has_weak_signal(masked) and llm_ok)
                    reason = "sem_sinal_de_dominio" if not has_weak_signal(masked) else "sinal_fraco_sem_classificador"
                if refuse:
                    decision = RouteDecision("fora_de_escopo", None, "fallback", 0.0)
                    scope_reason = reason
            if decision.source == "fallback" and decision.target_agent is not None and llm_ok:
                allowed = [key for key in RUNNERS if key in registry]
                llm_route = pre_route if pre_route is not None else await self._route_with_llm(masked, orchestrator, allowed, budget)
                first_line = (llm_route or "").strip().splitlines()[0].strip().lower() if llm_route else ""
                matched = next((key for key in allowed if key.lower() == first_line), None) or next(
                    (key for key in allowed if key in (llm_route or "")), None
                )
                if first_line.startswith("conversa"):
                    # saudação/agradecimento/meta que nem o embedding nem as listas reconheceram: boas-vindas, não recusa
                    decision = RouteDecision("fora_de_escopo", None, "fallback", 0.0)
                    scope_reason, chat_verdict = "classificador_conversa", True
                elif first_line.startswith("nenhum") or (llm_route or "").strip().lower()[:20].startswith("nenhum"):
                    # O classificador tem permissão explícita de dizer "não é comigo". Sem essa
                    # saída ele escolhe um agente por eliminação e o cliente recebe uma resposta
                    # sobre pedido para uma pergunta que não era sobre pedido — o pior desfecho.
                    decision = RouteDecision("fora_de_escopo", None, "fallback", 0.0)
                    scope_reason = "classificador_nenhum"
                elif matched:
                    decision = RouteDecision("classificacao_llm", matched, "orchestrator", 0.9)
                elif not has_domain_signal(masked):
                    # só palavra genérica e o classificador não decidiu (falhou/formato inesperado): orienta, não adivinha
                    decision = RouteDecision("fora_de_escopo", None, "fallback", 0.0)
                    scope_reason = "classificador_indisponivel"
        if decision.target_agent is None and decision.source == "fallback":
            # Fora do domínio: em vez de cair no order_agent com confiança 0.55 e responder
            # "alguma coisa" sobre pedido, o orquestrador assume o turno e orienta com o que
            # existe de verdade para esta identidade. Determinístico e sem custo de LLM.
            snapshot = await customer_snapshot(self.store, customer)
            if is_greeting(masked) or is_capabilities_question(masked):
                response, titulo = greeting_reply(snapshot, customer=customer), "Abertura de conversa — orquestrador apresenta o que existe para o cliente"
            elif is_thanks(masked):
                response, titulo = thanks_reply(snapshot, customer=customer), "Encerramento cordial — conversa segue aberta"
            elif is_meta_question(masked):
                response, titulo = meta_reply(snapshot, customer=customer), "Pergunta sobre o próprio atendimento — resposta honesta sobre a arquitetura"
            elif chat_verdict:
                response, titulo = greeting_reply(snapshot, customer=customer), "Conversa cordial — orquestrador apresenta o que existe para o cliente"
            else:
                response, titulo = out_of_scope_reply(snapshot, customer=customer), "Fora de escopo — orquestrador orienta com os dados reais do cliente"
            if titulo.startswith("Fora de escopo"):
                # visível no painel de guardrails: não é ataque (blocked=False) e não gastou agente nem LLM
                timeline.append(TimelineEvent(
                    category="guardrail", title="Guardrail de escopo: pergunta fora do domínio da loja",
                    result={"blocked": False, "out_of_scope": True, "reason": scope_reason or "sem_sinal_de_dominio"},
                ))
            timeline.append(TimelineEvent(
                category="agent",
                title=titulo,
                agent="orchestrator",
                collection="orders + invoices + loyalty_accounts + shipments",
                op="read",
                filter={"owner_customer_key": customer["customer_key"]},
                result={"sugestoes": [item["topic"] for item in build_suggestions(snapshot)]},
            ))
            await metrics.increment("routing.out_of_scope")
            trace_url = await self._persist_trace(conversation_id, customer, masked, response, timeline, "orchestrator", self._usage(budget), (perf_counter() - started) * 1000, llm_calls=budget.llm_calls)
            await _record_collection_metrics(timeline)
            return self._response(budget, conversation_id=conversation_id, response=response, active_agent="orchestrator", route_source="fallback", cache_hit=False, timeline=timeline, usage=self._usage(budget), suggestions=build_suggestions(snapshot), langfuse_trace_url=trace_url)

        target = decision.target_agent or "order_agent"
        route_source = decision.source
        if target not in registry:
            target = FALLBACK_AGENTS.get(target, "order_agent")
            if target not in registry:
                target = next((key for key in RUNNERS if key in registry), "order_agent")
            route_source = "fallback"
        timeline.append(TimelineEvent(category="agent", title="Roteamento inicial", agent=target, collection="multiagent_brain.routing_rules" if decision.source == "rules" else "multiagent_brain.agent_registry", op="read", filter={"intent": decision.intent}, result={"target_agent": target, "source": route_source, "confidence": decision.confidence}))

        if target == "product_agent" and await active_budget(self.store, customer["customer_key"]) is not None:
            # o cache guarda a recomendação SEM teto; quem tem orçamento ativo nunca a recebe (ignoraria o limite dele)
            cascade = CascadeResult(hit=False, personal_reason="orcamento")
        else:
            cascade = await cascade_lookup(self.store, target=target, area=customer["area"], customer_key=customer["customer_key"], session_id=conversation_id, message=masked)
        if cascade.hit:
            await metrics.increment(f"agent.{target}.cache_hits")
            await metrics.increment(f"cache.hits.{cascade.fonte}")
            await metrics.increment("tokens.economizados", cascade.tokens_economizados)
            timeline.append(TimelineEvent(category="cache", title=f"Cascata semântica: HIT ({cascade.fonte})", agent=target, collection="short_term_memory" if cascade.fonte == "curto_prazo" else "semantic_cache", op="vectorSearch", filter={"session_id": conversation_id, "agent": target}, result={"hit": True, "fonte": cascade.fonte, "score": cascade.score, "classifier_score": (cascade.classifier or {}).get("score")}))
            response = cascade.answer or ""
            cached_active_agent = cascade.active_agent or target
            cached_timeline = timeline + [TimelineEvent(**{**event, "replayed": True}) for event in cascade.timeline]
            # HIT também entra na memória de curto prazo: ela registra a CONVERSA, não o custo.
            await cascade_store_short_term(
                self.store, target=target, area=customer["area"], customer_key=customer["customer_key"],
                session_id=conversation_id, message=masked, answer=response,
                timeline=cascade.timeline or [],   # já vem como dict do documento cacheado
                active_agent=cached_active_agent,
            )
            await self._update_conversation(conversation_id, customer, masked, response, cached_active_agent, [], cached_timeline)
            trace_url = await self._persist_trace(conversation_id, customer, masked, response, cached_timeline, cached_active_agent, self._usage(budget), (perf_counter() - started) * 1000, llm_calls=budget.llm_calls)
            await _record_collection_metrics(cached_timeline)
            return self._response(budget, conversation_id=conversation_id, response=response, active_agent=cached_active_agent, route_source=route_source, cache_hit=True, cache_source=cascade.fonte, tokens_economizados=cascade.tokens_economizados, timeline=cached_timeline, usage=self._usage(budget), suggestions=await _next_steps(self.store, customer, covered={TOPIC_BY_AGENT.get(cached_active_agent, "")}), langfuse_trace_url=trace_url)
        timeline.append(TimelineEvent(category="cache", title="Cascata semântica: MISS (curto prazo + cache global)", agent=target, collection="short_term_memory", op="vectorSearch", filter={"session_id": conversation_id, "agent": target}, result={"hit": False, **({"personal": cascade.personal_reason, "classifier": cascade.classifier} if cascade.personal_reason else {})}))
        long_term = await cascade_long_term_context(self.store, customer_key=customer["customer_key"], message=masked)
        if long_term:
            timeline.append(TimelineEvent(category="memory", title="Memória de longo prazo recuperada (contexto pro prompt)", agent=target, collection="long_term_memory", op="vectorSearch", filter={"customer_key": customer["customer_key"]}, result={"count": len(long_term)}))
        tail_start = len(timeline)

        long_term_hint = (
            " Contexto de longo prazo sobre este cliente (memória semântica/episódica, não é resposta pronta, "
            "use só como pano de fundo): " + " | ".join(str(item.get("text", "")) for item in long_term)
        ) if long_term else ""
        recent_turns = (conversation or {}).get("turns", [])[-6:]
        history_hint = (
            " Histórico real desta conversa até agora, na ordem em que aconteceu (se o cliente perguntar "
            "o que ele já disse/perguntou antes, responda com base nisso, nunca diga que não tem registro): "
            + " | ".join(f"{item['role']}: {item['content']}" for item in recent_turns)
        ) if recent_turns else ""

        budget.reserve(target, estimate_tokens(masked))
        supervisor = _supervisor_state(conversation_id)
        handoff_chain: list[dict] = []
        responses: list[str] = []
        current = target
        visit_counts = {current: 1}
        handoff_path = [current]
        for hop in range(MAX_HOPS):
            runner = RUNNERS.get(current)
            if not runner:
                break
            if current in WRITE_EFFECT_AGENTS and hop > 0:
                # O registry do início do turno pode estar velho pelo tempo em que a cadeia chega
                # aqui — só importa para quem escreve: um agente de leitura desativado no meio do
                # turno no pior caso devolve uma resposta um pouco atrasada, mas um agente de
                # escrita desativado não pode processar resgate/status/reagendamento/chamado com
                # uma flag `active` que já não é mais verdade no banco.
                live_agent = await self.store.find_one("agent_registry", {"agent_key": current}, brain=True)
                if not live_agent or not live_agent.get("active", False):
                    responses.append(
                        f"O agente de destino ({current}) foi desativado durante o atendimento; "
                        "mantive a orientação já disponível sem processar esta etapa."
                    )
                    break
            if supervisor["strict"] and supervisor["guard"].visit(current, decision.intent):
                # Mesmo agente + mesma intenção além do limite: o supervisor corta a cadeia em vez
                # de girar gastando budget, e entrega o caso a um humano com motivo explícito.
                await metrics.increment("supervisor.loop_guard")
                responses.append(resilience.HUMAN_HANDOFF_REPLY)
                timeline.append(TimelineEvent(
                    category="handoff", title="Supervisor interrompeu: laço detectado", agent=current,
                    result={"loop_on": list(supervisor["guard"].tripped_on or ()), "escalated_to": "humano"},
                    reason="loop_guard"))
                break
            await metrics.increment(f"agent.{current}.turns")
            turn_context = {
                "conversation_id": conversation_id,
                "active_order_id": (conversation or {}).get("active_order_id"),
                "active_invoice_id": (conversation or {}).get("active_invoice_id"),
                "handoff_path": list(handoff_path),
                "visit_counts": dict(visit_counts),
                "returning_from": handoff_path[-2] if len(handoff_path) > 1 else None,
            }
            with observability.span("agent", agent=current, conversation_id=conversation_id, hop=hop,
                                    intent=decision.intent):
                async def _run_agent(agent_key=current, hint=(history_hint + long_term_hint) if hop == 0 else ""):
                    # O ponto de caos fica DENTRO da corrotina cronometrada: um agente travado
                    # só prova alguma coisa se o teto do supervisor o interromper de verdade.
                    await chaos.hook("agent", name=agent_key)
                    return await runner(self.store, masked, customer, self.llm, budget,
                                        registry.get(agent_key), hint, turn_context)

                call = _run_agent()
                if not supervisor["strict"]:
                    result = await call
                else:
                    try:
                        result = await resilience.run_with_timeout(call, supervisor["timeout"])
                    except BudgetExceeded:
                        raise   # limite de custo é decisão de política, não falha a degradar
                    except Exception as exc:  # noqa: BLE001 — degradação graciosa
                        # Um agente que falha ou não volta não pode terminar o turno em 500 nem em
                        # silêncio: o cliente recebe estado explícito e o turno segue sendo persistido.
                        await metrics.increment(f"agent.{current}.failures")
                        responses.append(resilience.degraded_reply(current))
                        timeline.append(TimelineEvent(
                            category="agent", title="Agente degradado (falha contida pelo supervisor)",
                            agent=current, result={"error_type": type(exc).__name__,
                                                   "timeout_seconds": supervisor["timeout"]}))
                        break
            timeline.append(result.event)
            timeline.extend(result.extra_events)
            responses.append(result.response)
            budget.reserve(current, estimate_tokens(result.response))
            if not result.handoff_to or hop == MAX_HOPS - 1:
                break
            destination = result.handoff_to
            if destination not in registry:
                destination = FALLBACK_AGENTS.get(destination, target)
            is_revisit = visit_counts.get(destination, 0) > 0
            revisit_allowed = (
                (current, destination) in ALLOWED_REVISITS
                and visit_counts.get(destination, 0) < MAX_VISITS_PER_AGENT
            )
            if destination == current or (is_revisit and not revisit_allowed):
                responses.append(
                    "O agente de destino está desativado ou já atuou neste turno; mantive a orientação disponível sem criar um handoff circular."
                )
                break
            # customer_key denormalizado: o Change Stream de /api/events/stream
            # filtra por dono direto no $match, sem um find_one extra por evento.
            handoff = {"conversation_id": conversation_id, "customer_key": customer["customer_key"], "from_agent": current, "to_agent": destination, "reason": result.handoff_reason, "at": utcnow()}
            with observability.span("handoff", **{"handoff.from": current, "handoff.to": destination,
                                                  "conversation_id": conversation_id,
                                                  "handoff.reason": result.handoff_reason or ""}):
                await self.store.insert_one("agent_handoffs", handoff)
            handoff_chain.append(handoff)
            timeline.append(TimelineEvent(category="handoff", title="Retorno controlado" if is_revisit else "Handoff explícito", agent=current, collection="agent_handoffs", op="write", filter={"conversation_id": conversation_id}, result={"to_agent": destination, "revisit": is_revisit}, reason=result.handoff_reason))
            await metrics.increment(f"agent.{current}.handoffs")
            if is_revisit:
                await metrics.increment("coordination.revisits")
            # Falha do provedor ENTRE handoffs: a cadeia já escreveu o handoff; o turno tem de
            # terminar com estado explícito, nunca com meia resposta e sem aviso.
            if chaos.enabled():
                try:
                    await chaos.hook("handoff", name=f"{current}->{destination}", phase="between_handoffs")
                except Exception as exc:  # noqa: BLE001
                    if not supervisor["strict"]:
                        raise
                    responses.append(resilience.degraded_reply(destination))
                    timeline.append(TimelineEvent(
                        category="handoff", title="Handoff degradado (falha contida pelo supervisor)",
                        agent=current, result={"error_type": type(exc).__name__, "to_agent": destination}))
                    break
            visit_counts[destination] = visit_counts.get(destination, 0) + 1
            handoff_path.append(destination)
            current = destination

        response = "\n\n".join(responses) or "Não foi possível concluir o atendimento com segurança."
        # Mensagem MISTA (ex.: "qual a temperatura? e onde está meu pedido?"): o agente respondeu a parte da loja; a parte
        # alheia não some em silêncio — o cliente é avisado do que ficou de fora. Turno assim nunca vai ao cache.
        left_out = out_of_scope_sentences(masked)
        if left_out and responses:
            response += "\n\n" + " ".join(f"Sobre “{sentence}”: isso foge do que eu resolvo por aqui, então segui só com o restante." for sentence in left_out)
        output_guardrail = await check_output(self.store, response, customer)
        timeline.append(TimelineEvent(category="guardrail", title="Guardrail de saída", result={"blocked": output_guardrail.blocked}))
        if output_guardrail.blocked:
            response = "A resposta foi retida pela política de segurança."

        turn_tail = timeline[tail_start:]
        cache_eligible = (
            decision.intent in GLOBAL_CACHE_INTENTS
            and not written_facts
            and not left_out
            # a resposta só depende do cliente se o turno USOU memória (ex.: orçamento no product_agent, que emite
            # um evento de memória); ter fatos gravados ou episódios (rótulos) não a torna pessoal.
            and all(event.category != "memory" for event in turn_tail)
            and not handoff_chain
            and current == target
            and all(event.op != "write" for event in turn_tail)
        )
        await cascade_store_turn(
            self.store,
            target=target,
            area=customer["area"],
            customer_key=customer["customer_key"],
            session_id=conversation_id,
            intent=decision.intent,
            message=masked,
            answer=response,
            timeline=[event.model_dump(mode="json") for event in turn_tail],
            active_agent=current,
            cache_eligible=cache_eligible,
        )
        await cascade_store_episode(self.store, customer_key=customer["customer_key"], intent=decision.intent, agent=current)
        timeline.append(TimelineEvent(category="memory", title="Episódio gravado em memória de longo prazo", agent=current, collection="long_term_memory", op="write", filter={"customer_key": customer["customer_key"]}, result={}))
        await self._update_conversation(conversation_id, customer, masked, response, current, handoff_chain, timeline)
        usage = {**budget.used_by_agent, "total": budget.total_used, "cache_read": budget.cache_read_tokens, "cache_write": budget.cache_write_tokens}
        await metrics.increment("tokens.total", budget.total_used)
        await metrics.increment("cache.misses")
        trace_url = await self._persist_trace(conversation_id, customer, masked, response, timeline, current, usage, (perf_counter() - started) * 1000, llm_calls=budget.llm_calls)
        await _record_collection_metrics(timeline)
        suggestions = await _next_steps(self.store, customer, covered={TOPIC_BY_AGENT.get(current, "")})
        return self._response(budget, conversation_id=conversation_id, response=response, active_agent=current, route_source=route_source, cache_hit=False, cache_source=None, tokens_economizados=0, timeline=timeline, usage=usage, suggestions=suggestions, langfuse_trace_url=trace_url)

    async def _run_fanout(self, targets: list[str], masked: str, customer: dict, registry: dict, budget: TurnBudget, conversation_id: str, conversation: dict | None, timeline: list[TimelineEvent], started: float) -> ChatResponse:
        """Pattern Parallel Fan-Out/Synthesis: agentes independentes rodam ao mesmo tempo (asyncio.gather), não
        em cadeia — cobre pedidos compostos tipo 'status do pedido e quanto devo' sem pagar 2 turnos de latência."""
        fanout_key = "+".join(targets)
        cascade = await cascade_lookup(self.store, target=fanout_key, area=customer["area"], customer_key=customer["customer_key"], session_id=conversation_id, message=masked)
        if cascade.hit:
            await metrics.increment(f"cache.hits.{cascade.fonte}")
            timeline.append(TimelineEvent(category="cache", title=f"Cascata semântica: HIT ({cascade.fonte})", collection="short_term_memory" if cascade.fonte == "curto_prazo" else "semantic_cache", op="vectorSearch", filter={"session_id": conversation_id, "agent": fanout_key}, result={"hit": True, "fonte": cascade.fonte, "score": cascade.score, "classifier_score": (cascade.classifier or {}).get("score")}))
            response = cascade.answer or ""
            cached_active_agent = cascade.active_agent or fanout_key
            cached_timeline = timeline + [TimelineEvent(**{**event, "replayed": True}) for event in cascade.timeline]
            await self._update_conversation(conversation_id, customer, masked, response, cached_active_agent, [], cached_timeline)
            trace_url = await self._persist_trace(conversation_id, customer, masked, response, cached_timeline, cached_active_agent, self._usage(budget), (perf_counter() - started) * 1000, llm_calls=budget.llm_calls)
            await _record_collection_metrics(cached_timeline)
            return self._response(budget, conversation_id=conversation_id, response=response, active_agent=cached_active_agent, route_source="fanout", cache_hit=True, cache_source=cascade.fonte, tokens_economizados=cascade.tokens_economizados, timeline=cached_timeline, usage=self._usage(budget), suggestions=await _next_steps(self.store, customer, covered={"order", "invoice"}), langfuse_trace_url=trace_url)
        timeline.append(TimelineEvent(category="cache", title="Cascata semântica: MISS (curto prazo + cache global)", collection="short_term_memory", op="vectorSearch", filter={"session_id": conversation_id, "agent": fanout_key}, result={"hit": False, **({"personal": cascade.personal_reason, "classifier": cascade.classifier} if cascade.personal_reason else {})}))
        tail_start = len(timeline)
        timeline.append(TimelineEvent(category="fanout", title="Despacho paralelo", collection="multiagent_brain.routing_rules", op="read", filter={"targets": targets}, result={"agents": targets}))
        for target in targets:
            budget.reserve(target, estimate_tokens(masked))
            await metrics.increment(f"agent.{target}.turns")
        area_labels = {"order_agent": "pedido/entrega", "billing_agent": "fatura/pagamento"}
        turn_context = {"conversation_id": conversation_id, "active_order_id": (conversation or {}).get("active_order_id"), "active_invoice_id": (conversation or {}).get("active_invoice_id")}
        results = await asyncio.gather(*[
            RUNNERS[target](
                self.store, masked, customer, self.llm, budget, registry.get(target),
                f" REGRA OBRIGATÓRIA: esta pergunta tem 2 partes e outro agente já está respondendo a outra em "
                f"paralelo. Sua resposta deve conter SOMENTE o assunto '{area_labels.get(target, target)}'. "
                f"Comece direto pela resposta sobre {area_labels.get(target, target)}. NÃO escreva nenhuma frase "
                f"sobre o outro assunto, nem para dizer que não tem acesso — apague esse pensamento, apenas não "
                f"mencione o outro tema em nenhuma hipótese.",
                turn_context,
            )
            for target in targets
        ])
        for target, result in zip(targets, results):
            timeline.append(result.event)
            timeline.extend(result.extra_events)
            budget.reserve(target, estimate_tokens(result.response))
        response = "\n\n".join(result.response for result in results)
        output_guardrail = await check_output(self.store, response, customer)
        timeline.append(TimelineEvent(category="guardrail", title="Guardrail de saída", result={"blocked": output_guardrail.blocked}))
        if output_guardrail.blocked:
            response = "A resposta foi retida pela política de segurança."
        current = fanout_key
        await cascade_store_turn(self.store, target=fanout_key, area=customer["area"], customer_key=customer["customer_key"], session_id=conversation_id, intent=None, message=masked, answer=response, timeline=[event.model_dump(mode="json") for event in timeline[tail_start:]], active_agent=current)
        await self._update_conversation(conversation_id, customer, masked, response, current, [], timeline)
        usage = {**budget.used_by_agent, "total": budget.total_used, "cache_read": budget.cache_read_tokens, "cache_write": budget.cache_write_tokens}
        await metrics.increment("tokens.total", budget.total_used)
        await metrics.increment("fanout.turns")
        await metrics.increment("cache.misses")
        trace_url = await self._persist_trace(conversation_id, customer, masked, response, timeline, current, usage, (perf_counter() - started) * 1000, llm_calls=budget.llm_calls)
        await _record_collection_metrics(timeline)
        suggestions = await _next_steps(self.store, customer, covered={"order", "invoice"})
        return self._response(budget, conversation_id=conversation_id, response=response, active_agent=current, route_source="fanout", cache_hit=False, cache_source=None, tokens_economizados=0, timeline=timeline, usage=usage, suggestions=suggestions, langfuse_trace_url=trace_url)

    async def _update_conversation(self, conversation_id: str, customer: dict, message: str, response: str, active_agent: str, handoffs: list[dict], timeline: list[TimelineEvent] | None = None) -> None:
        """Aplica só o DELTA deste turno via `update_one` atômico — nunca reescreve o documento inteiro.

        Antes disto, o turno lia `agent_conversations` uma única vez no início de `run_turn` e, no
        fim, fazia `replace_one` do documento inteiro reconstruído em memória. Dois turnos
        concorrentes na MESMA `conversation_id` (double-click do usuário, retry de rede sobrepondo a
        request original em voo sob timeout do LLM) liam o mesmo estado inicial; o `replace_one` que
        terminasse por último sobrescrevia o documento inteiro e apagava a mensagem do turno que
        terminou primeiro — um lost update clássico. `$push`/`$each`/`$slice` fazem o histórico
        crescer por append no servidor, então a ordem de chegada dos dois turnos não importa: os dois
        acabam presentes, na ordem em que cada um efetivamente terminou.
        """
        now = utcnow()
        turn_entries = [{"role": "user", "content": message, "at": now}, {"role": "assistant", "content": response, "at": now}]
        handoff_entries = [{key: value for key, value in item.items() if key != "conversation_id"} for item in handoffs]

        # "pedido/fatura ativo": último order_id/invoice_id que um agente de fato tocou NESTE turno — é
        # o que order_agent/billing_agent/warranty_agent/logistics_agent usam como contexto no PRÓXIMO
        # turno quando a mensagem não cita um PED-/FAT- explícito. Só entra no $set quando este turno
        # de fato produziu um valor: sem isso, dois turnos concorrentes (um que toca pedido, outro que
        # não) poderiam fazer o que não tocou nada sobrescrever o campo com um valor antigo por engano
        # — aqui ele simplesmente não menciona o campo, e o servidor preserva o que já estava lá.
        set_fields: dict = {"active_agent": active_agent, "updated_at": now}
        for event in timeline or []:
            if isinstance(event.result, dict) and event.result.get("order_id"):
                set_fields["active_order_id"] = event.result["order_id"]
            if isinstance(event.result, dict) and event.result.get("invoice_id"):
                set_fields["active_invoice_id"] = event.result["invoice_id"]

        update: dict = {
            "$setOnInsert": {"conversation_id": conversation_id, "customer_key": customer["customer_key"]},
            "$set": set_fields,
            # -20: mesmo teto de antes (20 mensagens / handoffs), agora aplicado pelo próprio
            # servidor a cada append, nunca por um recorte feito em memória sobre um snapshot velho.
            "$push": {"turns": {"$each": turn_entries, "$slice": -20}},
        }
        if handoff_entries:
            update["$push"]["handoff_chain"] = {"$each": handoff_entries, "$slice": -20}

        await self.store.update_one(
            "agent_conversations",
            {"conversation_id": conversation_id, "customer_key": customer["customer_key"]},
            update,
            upsert=True,
        )

    async def _persist_trace(self, conversation_id: str, customer: dict, message: str, response: str, timeline: list[TimelineEvent], active_agent: str, usage: dict, duration_ms: float = 0, llm_calls: list[dict] | None = None) -> str | None:
        await self.store.insert_one("agent_traces", {"conversation_id": conversation_id, "customer_key": customer["customer_key"], "area": customer["area"], "message": message, "response": response, "active_agent": active_agent, "timeline": [event.model_dump(mode="python") for event in timeline], "usage": usage, "llm_calls": llm_calls or [], "economics": summarize_calls(llm_calls or []), "duration_ms": round(duration_ms, 2), "at": utcnow()})
        # Uma trace Langfuse por turno cobrindo a timeline inteira (roteamento, cache, cada hop de
        # agente, handoffs, guardrails) — não só a decisão de cache isolada. Best-effort: uma falha
        # aqui nunca derruba a resposta já persistida acima.
        try:
            return build_turn_trace(conversation_id=conversation_id, customer_key=customer["customer_key"], message=message, response=response, timeline=timeline, active_agent=active_agent, usage=usage, llm_calls=llm_calls, settings=self.store.settings)
        except Exception:  # noqa: BLE001
            return None
