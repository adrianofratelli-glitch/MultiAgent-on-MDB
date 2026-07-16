import asyncio
import uuid
from time import perf_counter

from .agents import RUNNERS, semantic_cache_get, semantic_cache_put
from .budget import BudgetExceeded, TurnBudget, estimate_tokens
from .database import DataStore, utcnow
from .guardrails import check_input, check_output
from .llm import LLMGateway
from .memory import extract_and_store
from .metrics import metrics
from .models import ChatResponse, TimelineEvent
from .router import RouteDecision, cheap_route, deterministic_orchestrator, detect_fanout
from .security import mask_pii


async def _record_collection_metrics(timeline: list[TimelineEvent]) -> None:
    """Contador cumulativo de toque por collection+operação — alimenta o painel 'Coleções' no front,
    prova visual de que MongoDB é o único data store por trás de leitura, escrita, vector e hybrid search."""
    for event in timeline:
        if event.collection and event.op:
            await metrics.increment(f"collection.{event.collection}.{event.op}")


MAX_HOPS = 4  # cadeia mais longa que o "handoff único" original: mostra o multi-agent orquestrando de verdade
FALLBACK_AGENTS = {
    "product_agent": "support_agent",
    "support_agent": "order_agent",
    "billing_agent": "order_agent",
    "order_agent": "support_agent",
    "warranty_agent": "support_agent",
    "loyalty_agent": "order_agent",
    "logistics_agent": "order_agent",
}


class OrchestrationService:
    def __init__(self, store: DataStore, llm: LLMGateway, global_budget: int):
        self.store = store
        self.llm = llm
        self.global_budget = global_budget

    async def run_turn(self, message: str, customer: dict, conversation_id: str | None) -> ChatResponse:
        started = perf_counter()
        conversation_id = conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
        masked = mask_pii(message)
        timeline: list[TimelineEvent] = []

        agents, rules, memory, conversation = await asyncio.gather(
            self.store.find_many("agent_registry", {"active": True}, brain=True, limit=20),
            self.store.find_many("routing_rules", {}, brain=True, limit=100),
            self.store.find_many("customer_memory", {"customer_key": customer["customer_key"], "active": True}, limit=5),
            self.store.find_one("agent_conversations", {"conversation_id": conversation_id, "customer_key": customer["customer_key"]}),
        )
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
            response = "Não posso atender essa solicitação porque ela viola a política de segurança."
            await self._persist_trace(conversation_id, customer, masked, response, timeline, "guardrail", {})
            await _record_collection_metrics(timeline)
            return ChatResponse(conversation_id=conversation_id, response=response, active_agent="guardrail", route_source="fallback", cache_hit=False, timeline=timeline, usage={})

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
            if decision.source == "fallback" and orchestrator and self.llm.client:
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
                        "Chaves permitidas: " + ", ".join(allowed)
                    ),
                    budget=budget,
                )
                first_line = (llm_route or "").strip().splitlines()[0].strip().lower() if llm_route else ""
                matched = next((key for key in allowed if key.lower() == first_line), None) or next(
                    (key for key in allowed if key in (llm_route or "")), None
                )
                if matched:
                    decision = RouteDecision("classificacao_llm", matched, "orchestrator", 0.9)
        target = decision.target_agent or "order_agent"
        route_source = decision.source
        if target not in registry:
            target = FALLBACK_AGENTS.get(target, "order_agent")
            if target not in registry:
                target = next((key for key in RUNNERS if key in registry), "order_agent")
            route_source = "fallback"
        timeline.append(TimelineEvent(category="agent", title="Roteamento inicial", agent=target, collection="ai_brain.routing_rules" if decision.source == "rules" else "ai_brain.agent_registry", op="read", filter={"intent": decision.intent}, result={"target_agent": target, "source": route_source, "confidence": decision.confidence}))

        cached = await semantic_cache_get(self.store, target, customer["area"], customer["customer_key"], masked)
        if cached:
            await metrics.increment(f"agent.{target}.cache_hits")
            timeline.append(TimelineEvent(category="cache", title="Cache semântico do agente", agent=target, collection="semantic_cache", op="read", filter={"agent": target, "area": customer["area"], "customer_key": customer["customer_key"]}, result={"hit": True}))
            response = cached["answer"]
            cached_active_agent = cached.get("active_agent", target)
            cached_timeline = timeline + [TimelineEvent(**event) for event in cached.get("timeline", [])]
            await self._update_conversation(conversation_id, customer, conversation, masked, response, cached_active_agent, [])
            await self._persist_trace(conversation_id, customer, masked, response, cached_timeline, cached_active_agent, {})
            await _record_collection_metrics(cached_timeline)
            return ChatResponse(conversation_id=conversation_id, response=response, active_agent=cached_active_agent, route_source=route_source, cache_hit=True, timeline=cached_timeline, usage={})
        timeline.append(TimelineEvent(category="cache", title="Cache semântico do agente", agent=target, collection="semantic_cache", op="read", filter={"agent": target, "area": customer["area"], "customer_key": customer["customer_key"]}, result={"hit": False}))
        tail_start = len(timeline)

        budget.reserve(target, estimate_tokens(masked))
        handoff_chain: list[dict] = []
        responses: list[str] = []
        current = target
        visited = {current}
        for hop in range(MAX_HOPS):
            runner = RUNNERS.get(current)
            if not runner:
                break
            await metrics.increment(f"agent.{current}.turns")
            result = await runner(self.store, masked, customer, self.llm, budget, registry.get(current))
            timeline.append(result.event)
            timeline.extend(result.extra_events)
            responses.append(result.response)
            budget.reserve(current, estimate_tokens(result.response))
            if not result.handoff_to or hop == MAX_HOPS - 1:
                break
            destination = result.handoff_to
            if destination not in registry:
                destination = FALLBACK_AGENTS.get(destination, target)
            if destination == current or destination in visited:
                responses.append(
                    "O agente de destino está desativado ou já atuou neste turno; mantive a orientação disponível sem criar um handoff circular."
                )
                break
            visited.add(destination)
            handoff = {"conversation_id": conversation_id, "from_agent": current, "to_agent": destination, "reason": result.handoff_reason, "at": utcnow()}
            await self.store.insert_one("agent_handoffs", handoff)
            handoff_chain.append(handoff)
            timeline.append(TimelineEvent(category="handoff", title="Handoff explícito", agent=current, collection="agent_handoffs", op="write", filter={"conversation_id": conversation_id}, result={"to_agent": destination}, reason=result.handoff_reason))
            await metrics.increment(f"agent.{current}.handoffs")
            current = destination

        response = "\n\n".join(responses) or "Não foi possível concluir o atendimento com segurança."
        output_guardrail = await check_output(self.store, response, customer)
        timeline.append(TimelineEvent(category="guardrail", title="Guardrail de saída", result={"blocked": output_guardrail.blocked}))
        if output_guardrail.blocked:
            response = "A resposta foi retida pela política de segurança."

        await semantic_cache_put(self.store, target, customer["area"], customer["customer_key"], masked, response, [event.model_dump(mode="json") for event in timeline[tail_start:]], active_agent=current)
        await self._update_conversation(conversation_id, customer, conversation, masked, response, current, handoff_chain)
        usage = {**budget.used_by_agent, "total": budget.total_used}
        await metrics.increment("tokens.total", budget.total_used)
        await self._persist_trace(conversation_id, customer, masked, response, timeline, current, usage, (perf_counter() - started) * 1000)
        await _record_collection_metrics(timeline)
        return ChatResponse(conversation_id=conversation_id, response=response, active_agent=current, route_source=route_source, cache_hit=False, timeline=timeline, usage=usage)

    async def _run_fanout(self, targets: list[str], masked: str, customer: dict, registry: dict, budget: TurnBudget, conversation_id: str, conversation: dict | None, timeline: list[TimelineEvent], started: float) -> ChatResponse:
        """Pattern Parallel Fan-Out/Synthesis: agentes independentes rodam ao mesmo tempo (asyncio.gather), não
        em cadeia — cobre pedidos compostos tipo 'status do pedido e quanto devo' sem pagar 2 turnos de latência."""
        timeline.append(TimelineEvent(category="fanout", title="Despacho paralelo", collection="ai_brain.routing_rules", op="read", filter={"targets": targets}, result={"agents": targets}))
        for target in targets:
            budget.reserve(target, estimate_tokens(masked))
            await metrics.increment(f"agent.{target}.turns")
        area_labels = {"order_agent": "pedido/entrega", "billing_agent": "fatura/pagamento"}
        results = await asyncio.gather(*[
            RUNNERS[target](
                self.store, masked, customer, self.llm, budget, registry.get(target),
                f" REGRA OBRIGATÓRIA: esta pergunta tem 2 partes e outro agente já está respondendo a outra em "
                f"paralelo. Sua resposta deve conter SOMENTE o assunto '{area_labels.get(target, target)}'. "
                f"Comece direto pela resposta sobre {area_labels.get(target, target)}. NÃO escreva nenhuma frase "
                f"sobre o outro assunto, nem para dizer que não tem acesso — apague esse pensamento, apenas não "
                f"mencione o outro tema em nenhuma hipótese.",
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
        current = "+".join(targets)
        await self._update_conversation(conversation_id, customer, conversation, masked, response, current, [])
        usage = {**budget.used_by_agent, "total": budget.total_used}
        await metrics.increment("tokens.total", budget.total_used)
        await metrics.increment("fanout.turns")
        await self._persist_trace(conversation_id, customer, masked, response, timeline, current, usage, (perf_counter() - started) * 1000)
        await _record_collection_metrics(timeline)
        return ChatResponse(conversation_id=conversation_id, response=response, active_agent=current, route_source="fanout", cache_hit=False, timeline=timeline, usage=usage)

    async def _update_conversation(self, conversation_id: str, customer: dict, existing: dict | None, message: str, response: str, active_agent: str, handoffs: list[dict]) -> None:
        turns = list((existing or {}).get("turns", []))[-18:]
        turns.extend([{"role": "user", "content": message, "at": utcnow()}, {"role": "assistant", "content": response, "at": utcnow()}])
        chain = list((existing or {}).get("handoff_chain", []))[-18:] + [{key: value for key, value in item.items() if key != "conversation_id"} for item in handoffs]
        await self.store.replace_one("agent_conversations", {"conversation_id": conversation_id}, {"conversation_id": conversation_id, "customer_key": customer["customer_key"], "turns": turns, "active_agent": active_agent, "handoff_chain": chain[-20:], "updated_at": utcnow()}, upsert=True)

    async def _persist_trace(self, conversation_id: str, customer: dict, message: str, response: str, timeline: list[TimelineEvent], active_agent: str, usage: dict, duration_ms: float = 0) -> None:
        await self.store.insert_one("agent_traces", {"conversation_id": conversation_id, "customer_key": customer["customer_key"], "area": customer["area"], "message": message, "response": response, "active_agent": active_agent, "timeline": [event.model_dump(mode="python") for event in timeline], "usage": usage, "duration_ms": round(duration_ms, 2), "at": utcnow()})
