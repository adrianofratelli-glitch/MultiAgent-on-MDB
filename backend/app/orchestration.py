import asyncio
import uuid
from time import perf_counter

from .agents import RUNNERS
from .budget import TurnBudget, estimate_tokens
from .cascade import (GLOBAL_CACHE_INTENTS, cascade_long_term_context, cascade_lookup, cascade_store_episode,
                      cascade_store_short_term, cascade_store_turn)
from .database import DataStore, utcnow
from .guardrails import check_input, check_output
from .langfuse_client import log_cache_decision
from .llm import LLMGateway
from .memory import extract_and_store
from .metrics import metrics
from .models import ChatResponse, TimelineEvent
from .router import RouteDecision, cheap_route, deterministic_orchestrator, detect_fanout, has_domain_signal
from .guidance import (blocked_reply, build_suggestions, customer_snapshot, greeting_reply,
                       is_greeting, is_meta_question, is_thanks, looks_like_own_pii, meta_reply,
                       out_of_scope_reply, pii_block_reply, thanks_reply)
from .security import mask_pii


async def _record_collection_metrics(timeline: list[TimelineEvent]) -> None:
    """Contador cumulativo de toque por collection+operação — alimenta o painel 'Coleções' no front,
    prova visual de que MongoDB é o único data store por trás de leitura, escrita, vector e hybrid search."""
    for event in timeline:
        if event.collection and event.op:
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
        guardrail = await check_input(self.store, masked, customer, llm=self.llm, budget=budget, agent_doc=registry.get("orchestrator"), skip_semantic=quick_decision is not None)
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
            await self._persist_trace(conversation_id, customer, masked, response, timeline, "guardrail", {})
            await _record_collection_metrics(timeline)
            return ChatResponse(conversation_id=conversation_id, response=response, active_agent="guardrail", route_source="fallback", cache_hit=False, timeline=timeline, usage={}, suggestions=build_suggestions(snapshot))

        written_facts = await extract_and_store(self.store, customer["customer_key"], masked)
        if written_facts:
            timeline.append(TimelineEvent(category="memory", title="Fato extraído do turno e persistido (supersessão)", collection="customer_memory", op="write", filter={"customer_key": customer["customer_key"]}, result=written_facts))

        fanout_targets = detect_fanout(masked, rules)
        if fanout_targets and all(target in registry for target in fanout_targets):
            return await self._run_fanout(fanout_targets, masked, customer, registry, budget, conversation_id, conversation, timeline, started)

        decision = quick_decision
        if decision is None:
            decision = deterministic_orchestrator(masked)
            orchestrator = registry.get("orchestrator")
            # só consulta o LLM quando o determinístico não achou palavra-chave alguma (fallback puro, 0.55) —
            # se já identificou defeito/produto/fatura com confiança, essa decisão é mais estável que uma
            # classificação de LLM e não deve ser sobrescrita por variação de amostragem do modelo.
            if decision.source == "fallback" and not has_domain_signal(masked):
                # Nenhuma palavra do domínio inteiro apareceu: não vale pagar uma chamada de
                # classificação para descobrir que não é sobre a loja. Vale também quando o
                # LLM está fora (DEMO_MODE/CI) — a orientação é determinística.
                decision = RouteDecision("fora_de_escopo", None, "fallback", 0.0)
            elif decision.source == "fallback" and orchestrator and self.llm.client:
                allowed = [key for key in RUNNERS if key in registry]
                llm_route, _ = await self.llm.complete(
                    agent=orchestrator,
                    user_message=masked,
                    dynamic_context=(
                        "Classifique a intenção do cliente e escolha o agente certo. Responda com UMA linha, "
                        "só a chave, sem explicação.\n"
                        "order_agent: status, rastreio, troca ou reembolso de um PEDIDO já feito.\n"
                        "product_agent: recomendação/comparação de PRODUTOS do catálogo (fones, monitores, "
                        "teclados, mouses, carregadores, smartwatches etc.), mesmo sem usar a palavra 'produto'.\n"
                        "support_agent: problema técnico/defeito para diagnosticar antes de qualquer troca.\n"
                        "billing_agent: fatura, cobrança, valor a pagar, vencimento.\n"
                        "nenhum: a mensagem não é sobre atendimento desta loja (assunto aleatório, "
                        "teste, texto sem sentido) — responda exatamente 'nenhum' nesse caso, "
                        "NUNCA escolha um agente por eliminação.\n"
                        "Chaves permitidas: " + ", ".join(allowed) + ", nenhum"
                    ),
                    budget=budget,
                )
                first_line = (llm_route or "").strip().splitlines()[0].strip().lower() if llm_route else ""
                matched = next((key for key in allowed if key.lower() == first_line), None) or next(
                    (key for key in allowed if key in (llm_route or "")), None
                )
                if first_line.startswith("nenhum") or (llm_route or "").strip().lower()[:20].startswith("nenhum"):
                    # O classificador tem permissão explícita de dizer "não é comigo". Sem essa
                    # saída ele escolhe um agente por eliminação e o cliente recebe uma resposta
                    # sobre pedido para uma pergunta que não era sobre pedido — o pior desfecho.
                    decision = RouteDecision("fora_de_escopo", None, "fallback", 0.0)
                elif matched:
                    decision = RouteDecision("classificacao_llm", matched, "orchestrator", 0.9)
        if decision.target_agent is None and decision.source == "fallback":
            # Fora do domínio: em vez de cair no order_agent com confiança 0.55 e responder
            # "alguma coisa" sobre pedido, o orquestrador assume o turno e orienta com o que
            # existe de verdade para esta identidade. Determinístico e sem custo de LLM.
            snapshot = await customer_snapshot(self.store, customer)
            if is_greeting(masked):
                response, titulo = greeting_reply(snapshot, customer=customer), "Abertura de conversa — orquestrador apresenta o que existe para o cliente"
            elif is_thanks(masked):
                response, titulo = thanks_reply(snapshot, customer=customer), "Encerramento cordial — conversa segue aberta"
            elif is_meta_question(masked):
                response, titulo = meta_reply(snapshot, customer=customer), "Pergunta sobre o próprio atendimento — resposta honesta sobre a arquitetura"
            else:
                response, titulo = out_of_scope_reply(snapshot, customer=customer), "Fora de escopo — orquestrador orienta com os dados reais do cliente"
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
            await self._persist_trace(conversation_id, customer, masked, response, timeline, "orchestrator", {})
            await _record_collection_metrics(timeline)
            return ChatResponse(conversation_id=conversation_id, response=response, active_agent="orchestrator", route_source="fallback", cache_hit=False, timeline=timeline, usage={}, suggestions=build_suggestions(snapshot))

        target = decision.target_agent or "order_agent"
        route_source = decision.source
        if target not in registry:
            target = FALLBACK_AGENTS.get(target, "order_agent")
            if target not in registry:
                target = next((key for key in RUNNERS if key in registry), "order_agent")
            route_source = "fallback"
        timeline.append(TimelineEvent(category="agent", title="Roteamento inicial", agent=target, collection="multiagent_brain.routing_rules" if decision.source == "rules" else "multiagent_brain.agent_registry", op="read", filter={"intent": decision.intent}, result={"target_agent": target, "source": route_source, "confidence": decision.confidence}))

        cascade = await cascade_lookup(self.store, target=target, area=customer["area"], customer_key=customer["customer_key"], session_id=conversation_id, message=masked)
        if cascade.hit:
            await metrics.increment(f"agent.{target}.cache_hits")
            await metrics.increment(f"cache.hits.{cascade.fonte}")
            await metrics.increment("tokens.economizados", cascade.tokens_economizados)
            timeline.append(TimelineEvent(category="cache", title=f"Cascata semântica: HIT ({cascade.fonte})", agent=target, collection="short_term_memory" if cascade.fonte == "curto_prazo" else "semantic_cache", op="vectorSearch", filter={"session_id": conversation_id, "agent": target}, result={"hit": True, "fonte": cascade.fonte, "score": cascade.score}))
            response = cascade.answer or ""
            cached_active_agent = cascade.active_agent or target
            cached_timeline = timeline + [TimelineEvent(**event) for event in cascade.timeline]
            log_cache_decision(conversation_id=conversation_id, customer_key=customer["customer_key"], message=masked, cache="hit", fonte=cascade.fonte, score=cascade.score, tokens_economizados=cascade.tokens_economizados, memorias_recuperadas=0, response=response)
            # HIT também entra na memória de curto prazo: ela registra a CONVERSA, não o custo.
            await cascade_store_short_term(
                self.store, target=target, area=customer["area"], customer_key=customer["customer_key"],
                session_id=conversation_id, message=masked, answer=response,
                timeline=cascade.timeline or [],   # já vem como dict do documento cacheado
                active_agent=cached_active_agent,
            )
            await self._update_conversation(conversation_id, customer, masked, response, cached_active_agent, [], cached_timeline)
            await self._persist_trace(conversation_id, customer, masked, response, cached_timeline, cached_active_agent, {})
            await _record_collection_metrics(cached_timeline)
            return ChatResponse(conversation_id=conversation_id, response=response, active_agent=cached_active_agent, route_source=route_source, cache_hit=True, cache_source=cascade.fonte, tokens_economizados=cascade.tokens_economizados, timeline=cached_timeline, usage={}, suggestions=await _next_steps(self.store, customer, covered={TOPIC_BY_AGENT.get(cached_active_agent, "")}))
        timeline.append(TimelineEvent(category="cache", title="Cascata semântica: MISS (curto prazo + cache global)", agent=target, collection="short_term_memory", op="vectorSearch", filter={"session_id": conversation_id, "agent": target}, result={"hit": False}))
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
            await metrics.increment(f"agent.{current}.turns")
            turn_context = {
                "conversation_id": conversation_id,
                "active_order_id": (conversation or {}).get("active_order_id"),
                "active_invoice_id": (conversation or {}).get("active_invoice_id"),
                "handoff_path": list(handoff_path),
                "visit_counts": dict(visit_counts),
                "returning_from": handoff_path[-2] if len(handoff_path) > 1 else None,
            }
            result = await runner(self.store, masked, customer, self.llm, budget, registry.get(current), (history_hint + long_term_hint) if hop == 0 else "", turn_context)
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
            await self.store.insert_one("agent_handoffs", handoff)
            handoff_chain.append(handoff)
            timeline.append(TimelineEvent(category="handoff", title="Retorno controlado" if is_revisit else "Handoff explícito", agent=current, collection="agent_handoffs", op="write", filter={"conversation_id": conversation_id}, result={"to_agent": destination, "revisit": is_revisit}, reason=result.handoff_reason))
            await metrics.increment(f"agent.{current}.handoffs")
            if is_revisit:
                await metrics.increment("coordination.revisits")
            visit_counts[destination] = visit_counts.get(destination, 0) + 1
            handoff_path.append(destination)
            current = destination

        response = "\n\n".join(responses) or "Não foi possível concluir o atendimento com segurança."
        output_guardrail = await check_output(self.store, response, customer)
        timeline.append(TimelineEvent(category="guardrail", title="Guardrail de saída", result={"blocked": output_guardrail.blocked}))
        if output_guardrail.blocked:
            response = "A resposta foi retida pela política de segurança."

        turn_tail = timeline[tail_start:]
        cache_eligible = (
            decision.intent in GLOBAL_CACHE_INTENTS
            and not memory
            and not written_facts
            and not long_term
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
        await cascade_store_episode(self.store, customer_key=customer["customer_key"], message=masked, answer=response)
        timeline.append(TimelineEvent(category="memory", title="Episódio gravado em memória de longo prazo", agent=current, collection="long_term_memory", op="write", filter={"customer_key": customer["customer_key"]}, result={}))
        await self._update_conversation(conversation_id, customer, masked, response, current, handoff_chain, timeline)
        usage = {**budget.used_by_agent, "total": budget.total_used, "cache_read": budget.cache_read_tokens, "cache_write": budget.cache_write_tokens}
        await metrics.increment("tokens.total", budget.total_used)
        await metrics.increment("cache.misses")
        log_cache_decision(conversation_id=conversation_id, customer_key=customer["customer_key"], message=masked, cache="miss", fonte=None, score=None, tokens_economizados=0, memorias_recuperadas=len(long_term), response=response, usage=usage)
        await self._persist_trace(conversation_id, customer, masked, response, timeline, current, usage, (perf_counter() - started) * 1000)
        await _record_collection_metrics(timeline)
        suggestions = await _next_steps(self.store, customer, covered={TOPIC_BY_AGENT.get(current, "")})
        return ChatResponse(conversation_id=conversation_id, response=response, active_agent=current, route_source=route_source, cache_hit=False, cache_source=None, tokens_economizados=0, timeline=timeline, usage=usage, suggestions=suggestions)

    async def _run_fanout(self, targets: list[str], masked: str, customer: dict, registry: dict, budget: TurnBudget, conversation_id: str, conversation: dict | None, timeline: list[TimelineEvent], started: float) -> ChatResponse:
        """Pattern Parallel Fan-Out/Synthesis: agentes independentes rodam ao mesmo tempo (asyncio.gather), não
        em cadeia — cobre pedidos compostos tipo 'status do pedido e quanto devo' sem pagar 2 turnos de latência."""
        fanout_key = "+".join(targets)
        cascade = await cascade_lookup(self.store, target=fanout_key, area=customer["area"], customer_key=customer["customer_key"], session_id=conversation_id, message=masked)
        if cascade.hit:
            await metrics.increment(f"cache.hits.{cascade.fonte}")
            timeline.append(TimelineEvent(category="cache", title=f"Cascata semântica: HIT ({cascade.fonte})", collection="short_term_memory" if cascade.fonte == "curto_prazo" else "semantic_cache", op="vectorSearch", filter={"session_id": conversation_id, "agent": fanout_key}, result={"hit": True, "fonte": cascade.fonte, "score": cascade.score}))
            response = cascade.answer or ""
            cached_active_agent = cascade.active_agent or fanout_key
            cached_timeline = timeline + [TimelineEvent(**event) for event in cascade.timeline]
            log_cache_decision(conversation_id=conversation_id, customer_key=customer["customer_key"], message=masked, cache="hit", fonte=cascade.fonte, score=cascade.score, tokens_economizados=cascade.tokens_economizados, memorias_recuperadas=0, response=response)
            await self._update_conversation(conversation_id, customer, masked, response, cached_active_agent, [], cached_timeline)
            await self._persist_trace(conversation_id, customer, masked, response, cached_timeline, cached_active_agent, {})
            await _record_collection_metrics(cached_timeline)
            return ChatResponse(conversation_id=conversation_id, response=response, active_agent=cached_active_agent, route_source="fanout", cache_hit=True, cache_source=cascade.fonte, tokens_economizados=cascade.tokens_economizados, timeline=cached_timeline, usage={}, suggestions=await _next_steps(self.store, customer, covered={"order", "invoice"}))
        timeline.append(TimelineEvent(category="cache", title="Cascata semântica: MISS (curto prazo + cache global)", collection="short_term_memory", op="vectorSearch", filter={"session_id": conversation_id, "agent": fanout_key}, result={"hit": False}))
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
        log_cache_decision(conversation_id=conversation_id, customer_key=customer["customer_key"], message=masked, cache="miss", fonte=None, score=None, tokens_economizados=0, memorias_recuperadas=0, response=response, usage=usage)
        await self._persist_trace(conversation_id, customer, masked, response, timeline, current, usage, (perf_counter() - started) * 1000)
        await _record_collection_metrics(timeline)
        suggestions = await _next_steps(self.store, customer, covered={"order", "invoice"})
        return ChatResponse(conversation_id=conversation_id, response=response, active_agent=current, route_source="fanout", cache_hit=False, cache_source=None, tokens_economizados=0, timeline=timeline, usage=usage, suggestions=suggestions)

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

    async def _persist_trace(self, conversation_id: str, customer: dict, message: str, response: str, timeline: list[TimelineEvent], active_agent: str, usage: dict, duration_ms: float = 0) -> None:
        await self.store.insert_one("agent_traces", {"conversation_id": conversation_id, "customer_key": customer["customer_key"], "area": customer["area"], "message": message, "response": response, "active_agent": active_agent, "timeline": [event.model_dump(mode="python") for event in timeline], "usage": usage, "duration_ms": round(duration_ms, 2), "at": utcnow()})
