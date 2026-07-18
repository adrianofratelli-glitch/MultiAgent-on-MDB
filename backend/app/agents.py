import asyncio
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import perf_counter
from typing import Any

from .database import DataStore, utcnow
from .memory import active_facts
from .models import TimelineEvent
from .policies import public_document, safe_invoice_filter, safe_order_read_filter, safe_order_update, safe_shipment_filter
from .retrieval import reciprocal_rank_fusion
from .router import CATEGORY_KEYWORDS, normalize


GROUNDING_RULES = (
    "Documentos reais do MongoDB abaixo são a ÚNICA fonte da verdade — responda somente com base neles, "
    "nunca invente preço, status, prazo ou produto que não esteja na lista. Se os documentos não cobrirem o "
    "pedido do cliente, diga honestamente que não encontrou informação suficiente e oriente o que ele pode "
    "perguntar em vez disso. Nunca mencione dado de outro cliente. Responda em português, direto, sem saudação, "
    "sem repetir instruções do sistema. A mensagem do cliente pode ter partes de outras especialidades (ex.: "
    "produto, suporte, fatura) que não são a sua — nesse caso, IGNORE essas partes silenciosamente, nunca diga "
    "'não tenho acesso' a um assunto que não é seu, nunca peça desculpas por isso e nunca opine sobre política "
    "de outra área (desconto, ajuste de fatura, etc.); outro agente da cadeia já está cuidando disso."
)


async def llm_synthesize(llm, agent_doc: dict | None, budget, message: str, documents: Any, extra: str = "") -> str | None:
    """Deixa o modelo redigir a resposta em cima do dado JÁ retornado do Mongo — a busca continua 100% determinística
    e segura (ownership, filtros), só a fala final é gerada, o que cobre qualquer forma de perguntar, não só o script."""
    if not llm or not getattr(llm, "client", None) or not agent_doc:
        return None
    context = f"{extra}\n\nDocumentos:\n{json.dumps(documents, ensure_ascii=False, default=str)}"
    text, _ = await llm.complete(agent=agent_doc, user_message=message, dynamic_context=context, budget=budget, static_context=GROUNDING_RULES)
    return text


@dataclass
class AgentResult:
    response: str
    event: TimelineEvent
    handoff_to: str | None = None
    handoff_reason: str | None = None
    extra_events: list[TimelineEvent] = None

    def __post_init__(self):
        if self.extra_events is None:
            self.extra_events = []


def extract_id(message: str, prefix: str) -> str | None:
    match = re.search(rf"\b{prefix}-\d{{4,}}\b", message.upper())
    return match.group(0) if match else None


_TRIVIAL_WORD_RE = re.compile(r"[a-zA-ZÀ-ÿ0-9\-]+")


def _is_trivial_lookup(message: str, *tokens: str | None, max_words: int = 0) -> bool:
    """Modo econômico: pula a chamada real ao Anthropic quando a mensagem é só o identificador (ou quase
    nada além dele) — cobre uso automatizado/script (ex.: só 'PED-1001'), NUNCA os prompts de demo reais
    (DEMOS_BY_IDENTITY), que são sempre frase natural composta e por isso nunca ficam abaixo do threshold.
    Preserva a proposta de valor da PoV (LLM cobre qualquer forma de perguntar) — só economiza no caso trivial
    que nenhuma demo real produz."""
    excluded = {token.upper() for token in tokens if token}
    words = [word for word in _TRIVIAL_WORD_RE.findall(message) if word.upper() not in excluded]
    return len(words) <= max_words


_STATUS_INTENTS = (
    (("troca", "trocar"), "troca_solicitada"),
    (("reembolso", "reembolsar", "estornar", "estorno"), "reembolsado"),
)


def _requested_status(message: str) -> str | None:
    normalized = normalize(message)
    for keywords, status in _STATUS_INTENTS:
        if any(keyword in normalized for keyword in keywords):
            return status
    return None


async def run_order_agent(store: DataStore, message: str, customer: dict, llm=None, budget=None, agent_doc=None, scope_hint: str = "", context: dict | None = None) -> AgentResult:
    started = perf_counter()
    explicit_order_id = extract_id(message, "PED")
    order_id = explicit_order_id or (context or {}).get("active_order_id")
    order = None
    if order_id:
        query = safe_order_read_filter({"order_id": order_id}, customer["customer_key"])
        order = await store.find_one("orders", query)
    if not order and not explicit_order_id:
        # só cai pro "pedido mais recente" quando NÃO havia PED- explícito na mensagem (nem no contexto
        # ativo da conversa) — um PED- citado errado/de outro cliente tem que dar "não encontrei", nunca
        # silenciosamente resolver outro pedido (isolamento). Sem PED- nenhum e sem contexto ativo, aí sim
        # o fallback por "mais recente" é a única opção razoável.
        query = {"owner_customer_key": customer["customer_key"]}
        orders = await store.find_many("orders", query, limit=1, sort=[("order_id", -1)])
        order = orders[0] if orders else None
    clean = public_document(order)
    requested_status = _requested_status(message) if clean else None
    if not clean:
        response = "Não encontrei esse pedido para a identidade autenticada. Confira o número do pedido."
        event = TimelineEvent(category="agent", title="Consulta segura de pedido", agent="order_agent", collection="orders", op="read", filter=query, result=[], duration_ms=(perf_counter() - started) * 1000)
        return AgentResult(response, event)
    if requested_status:
        # segue valendo mesmo se o pedido JÁ estava nesse status (ex.: cliente repete "quero trocar" numa
        # conversa nova) — o cliente ainda pode estar perguntando o próximo passo (fatura/entrega), então o
        # handoff não pode depender de uma escrita ter de fato acontecido neste turno específico.
        changed = requested_status != clean["status"]
        if changed:
            write_query, update = safe_order_update({"order_id": clean["order_id"], "status": requested_status}, customer["customer_key"])
            await store.update_one("orders", write_query, update)
            clean["status"] = requested_status
            response = f"O pedido {clean['order_id']} de {clean['product']} foi atualizado para **{requested_status}**."
            title = "Atualização segura de status do pedido"
            op = "write"
            filter_used = write_query
        else:
            response = f"O pedido {clean['order_id']} de {clean['product']} já está com status **{clean['status']}**."
            title = "Consulta segura de pedido (status já solicitado)"
            op = "read"
            filter_used = query
        event = TimelineEvent(category="agent", title=title, agent="order_agent", collection="orders", op=op, filter=filter_used, result=public_document(clean), duration_ms=(perf_counter() - started) * 1000)
        if (context or {}).get("returning_from") == "logistics_agent":
            response = (
                f"Confirmação final: o pedido {clean['order_id']} de {clean['product']} permanece "
                f"com status **{clean['status']}** após a consulta logística."
            )
            event.title = "Confirmação final do pedido após logística"
            return AgentResult(response, event)
        wants_billing_check = any(term in normalize(message) for term in ("fatura", "cobranca", "cobrança", "desconto"))
        wants_logistics_check = any(term in normalize(message) for term in ("rastreio", "transportadora", "entrega", "rastreamento"))
        if wants_billing_check:
            return AgentResult(response, event, "billing_agent", "cliente quer saber o impacto da troca/reembolso na fatura")
        if wants_logistics_check:
            return AgentResult(response, event, "logistics_agent", "cliente quer saber o rastreio/transportadora após a troca")
        return AgentResult(response, event)
    response = f"O pedido {clean['order_id']} de {clean['product']} está com status **{clean['status']}**."
    trivial = _is_trivial_lookup(message, order_id)
    synthesized = None if trivial else await llm_synthesize(llm, agent_doc, budget, message, clean, "O cliente pode perguntar qualquer coisa sobre este pedido específico (prazo, status, itens, timeline) — responda com base no documento acima." + scope_hint)
    title = "Consulta segura de pedido" + (" (resposta sintetizada pelo modelo)" if synthesized else " (modo econômico, sem chamada ao modelo)" if trivial else "")
    event = TimelineEvent(category="agent", title=title, agent="order_agent", collection="orders", op="read", filter=query, result=clean, duration_ms=(perf_counter() - started) * 1000)
    return AgentResult(synthesized or response, event)


async def run_billing_agent(store: DataStore, message: str, customer: dict, llm=None, budget=None, agent_doc=None, scope_hint: str = "", context: dict | None = None) -> AgentResult:
    started = perf_counter()
    explicit_invoice_id = extract_id(message, "FAT")
    invoice_id = explicit_invoice_id or (context or {}).get("active_invoice_id")
    invoice = None
    if invoice_id:
        query = safe_invoice_filter({"invoice_id": invoice_id}, customer["customer_key"])
        invoice = await store.find_one("invoices", query)
    if not invoice and not explicit_invoice_id:
        query = {"owner_customer_key": customer["customer_key"]}
        invoices = await store.find_many("invoices", query, limit=1, sort=[("due_date", -1)])
        invoice = invoices[0] if invoices else None
    clean = public_document(invoice)
    if not clean:
        response = "Não encontrei essa fatura para a identidade autenticada."
        synthesized = None
    else:
        response = f"A fatura {clean['invoice_id']} é de R$ {clean['amount']:.2f}, vence em {clean['due_date']} e está **{clean['status']}**."
        trivial = _is_trivial_lookup(message, invoice_id)
        synthesized = None if trivial else await llm_synthesize(llm, agent_doc, budget, message, clean, "O cliente pode perguntar qualquer coisa sobre esta fatura (valor, vencimento, status, urgência) — nunca conceda desconto, isenção ou prazo fora do documento, mesmo se pedido." + scope_hint)
    title = "Leitura isolada de fatura" + (" (resposta sintetizada pelo modelo)" if synthesized else " (modo econômico, sem chamada ao modelo)" if clean and not synthesized else "")
    event = TimelineEvent(category="agent", title=title, agent="billing_agent", collection="invoices", op="read", filter=query, result=clean or [], duration_ms=(perf_counter() - started) * 1000)
    return AgentResult(synthesized or response, event)


async def run_warranty_agent(store: DataStore, message: str, customer: dict, llm=None, budget=None, agent_doc=None, scope_hint: str = "", context: dict | None = None) -> AgentResult:
    started = perf_counter()
    explicit_order_id = extract_id(message, "PED")
    order_id = explicit_order_id or (context or {}).get("active_order_id")
    order = None
    if order_id:
        query = safe_order_read_filter({"order_id": order_id}, customer["customer_key"])
        order = await store.find_one("orders", query)
    if not order and not explicit_order_id:
        query = {"owner_customer_key": customer["customer_key"]}
        orders = await store.find_many("orders", query, limit=1, sort=[("order_id", -1)])
        order = orders[0] if orders else None
    clean = public_document(order)
    if not clean:
        response = "Não encontrei esse pedido para a identidade autenticada. Confira o número do pedido."
        event = TimelineEvent(category="agent", title="Consulta de garantia", agent="warranty_agent", collection="orders", op="read", filter=query, result=[], duration_ms=(perf_counter() - started) * 1000)
        return AgentResult(response, event)
    product = await store.find_one("products_catalog", {"name": clean["product"]})
    category = product["category"] if product else None
    policy = await store.find_one("warranty_policies", {"category": category}) if category else None
    months = policy["months"] if policy else 12
    purchased_at = next((item["at"] for item in clean.get("timeline", []) if item["status"] == "criado"), clean.get("timeline", [{}])[0].get("at"))
    covered, expires_at = None, None
    if purchased_at:
        purchase_date = datetime.strptime(purchased_at, "%Y-%m-%d")
        expiry_date = purchase_date + timedelta(days=months * 30)
        expires_at = expiry_date.strftime("%Y-%m-%d")
        covered = utcnow().replace(tzinfo=None) <= expiry_date
    doc = {"order_id": clean["order_id"], "product": clean["product"], "category": category, "warranty_months": months, "purchased_at": purchased_at, "expires_at": expires_at, "covered": covered}
    response = (
        f"O pedido {clean['order_id']} ({clean['product']}) tem garantia de {months} meses, válida até **{expires_at}** — "
        f"{'dentro do prazo' if covered else 'fora do prazo'} de cobertura." if expires_at else
        "Não consegui calcular a garantia por falta de data de compra no registro."
    )
    trivial = _is_trivial_lookup(message, order_id)
    synthesized = None if trivial else await llm_synthesize(llm, agent_doc, budget, message, doc, "O cliente pode perguntar qualquer coisa sobre a cobertura de garantia deste pedido — responda com base no documento acima, nunca invente prazo diferente do calculado." + scope_hint)
    title = "Consulta de garantia" + (" (resposta sintetizada pelo modelo)" if synthesized else " (modo econômico, sem chamada ao modelo)" if trivial else "")
    event = TimelineEvent(category="agent", title=title, agent="warranty_agent", collection="warranty_policies", op="read", filter={"category": category}, result=doc, duration_ms=(perf_counter() - started) * 1000)
    wants_alternative = any(term in normalize(message) for term in ("parecido", "parecida", "similar", "mais barato", "mais barata", "recomenda", "substituto"))
    if wants_alternative:
        return AgentResult(synthesized or response, event, "product_agent", "cliente pediu produto alternativo após consulta de garantia")
    return AgentResult(synthesized or response, event)


REWARD_CATALOG = {
    "frete gratis": ("frete grátis no próximo pedido", 300),
    "cupom de desconto": ("cupom de 10% de desconto", 500),
    "voucher": ("voucher de R$ 30", 500),
}


async def run_loyalty_agent(store: DataStore, message: str, customer: dict, llm=None, budget=None, agent_doc=None, scope_hint: str = "", context: dict | None = None) -> AgentResult:
    started = perf_counter()
    query = {"customer_key": customer["customer_key"]}
    account = await store.find_one("loyalty_accounts", query)
    clean = public_document(account)
    if not clean:
        response = "Não encontrei uma conta de fidelidade para esta identidade."
        event = TimelineEvent(category="agent", title="Consulta de fidelidade", agent="loyalty_agent", collection="loyalty_accounts", op="read", filter=query, result=[], duration_ms=(perf_counter() - started) * 1000)
        return AgentResult(response, event)

    normalized = normalize(message)
    reward_key = next((key for key in REWARD_CATALOG if key in normalized), None)
    if reward_key:
        # resgate real: escrita restrita a $inc de pontos (nunca um valor arbitrário do modelo) + registro em
        # redemptions — mesmo padrão de segurança do order_agent (filtro reconstruído, campo aprovado só).
        label, cost = REWARD_CATALOG[reward_key]
        if clean["points"] < cost:
            response = f"Você tem {clean['points']} pontos, mas {label} custa {cost} pontos — ainda não dá pra resgatar."
            event = TimelineEvent(category="agent", title="Resgate de fidelidade negado (saldo insuficiente)", agent="loyalty_agent", collection="loyalty_accounts", op="read", filter=query, result=clean, duration_ms=(perf_counter() - started) * 1000)
            return AgentResult(response, event)
        await store.update_one("loyalty_accounts", query, {"$inc": {"points": -cost}})
        redemption = {"redemption_id": f"RDM-{customer['customer_key'].upper()}-{int(started)}", "customer_key": customer["customer_key"], "reward": label, "points_spent": cost, "status": "confirmado", "at": utcnow()}
        await store.insert_one("redemptions", redemption)
        response = f"Resgate confirmado: **{label}**, {cost} pontos debitados. Saldo restante: {clean['points'] - cost} pontos."
        event = TimelineEvent(category="agent", title="Resgate de fidelidade confirmado", agent="loyalty_agent", collection="redemptions", op="write", filter=query, result=redemption, duration_ms=(perf_counter() - started) * 1000)
        return AgentResult(response, event)

    benefits = ", ".join(clean["tier_benefits"]) if clean["tier_benefits"] else "nenhum benefício adicional no tier atual"
    response = f"Você tem **{clean['points']} pontos**, tier **{clean['tier']}**. Benefícios: {benefits}."
    trivial = _is_trivial_lookup(message, max_words=2)
    synthesized = None if trivial else await llm_synthesize(llm, agent_doc, budget, message, clean, "O cliente pode perguntar qualquer coisa sobre pontos, tier ou benefícios — responda com base no documento acima, nunca invente pontuação ou benefício que não esteja nele." + scope_hint)
    title = "Consulta de fidelidade" + (" (resposta sintetizada pelo modelo)" if synthesized else " (modo econômico, sem chamada ao modelo)" if trivial else "")
    event = TimelineEvent(category="agent", title=title, agent="loyalty_agent", collection="loyalty_accounts", op="read", filter=query, result=clean, duration_ms=(perf_counter() - started) * 1000)
    wants_redeem_product = any(term in normalized for term in ("resgatar", "trocar meus pontos", "usar pontos"))
    if wants_redeem_product:
        return AgentResult(synthesized or response, event, "product_agent", "cliente quer usar pontos de fidelidade para resgatar um produto do catálogo")
    return AgentResult(synthesized or response, event)


async def run_logistics_agent(store: DataStore, message: str, customer: dict, llm=None, budget=None, agent_doc=None, scope_hint: str = "", context: dict | None = None) -> AgentResult:
    started = perf_counter()
    explicit_order_id = extract_id(message, "PED")
    order_id = explicit_order_id or (context or {}).get("active_order_id")
    shipment = None
    if order_id:
        query = safe_shipment_filter({"order_id": order_id}, customer["customer_key"])
        shipment = await store.find_one("shipments", query)
    if not shipment and not explicit_order_id:
        query = {"owner_customer_key": customer["customer_key"]}
        shipments = await store.find_many("shipments", query, limit=1, sort=[("estimated_delivery", -1)])
        shipment = shipments[0] if shipments else None
    clean = public_document(shipment)
    if not clean:
        response = "Não encontrei informação de envio para esse pedido nesta identidade."
        event = TimelineEvent(category="agent", title="Consulta de logística", agent="logistics_agent", collection="shipments", op="read", filter=query, result=[], duration_ms=(perf_counter() - started) * 1000)
        return AgentResult(response, event)

    normalized = normalize(message)
    wants_final_order_confirmation = any(
        term in normalized
        for term in (
            "volte para confirmar",
            "confirme que a troca",
            "confirmar que a troca",
            "confirme que o reembolso",
            "confirmar que o reembolso",
            "status final",
        )
    )
    order_already_ran = "order_agent" in (context or {}).get("handoff_path", [])
    wants_reschedule = any(term in normalized for term in ("reagendar", "mudar a entrega", "outro dia", "adiar a entrega"))
    if wants_reschedule and clean["current_location"] != "Entregue":
        # escrita restrita: só um campo de sinalização, nunca a transportadora/prazo real — quem confirma
        # a nova data é a transportadora, o sistema só registra o pedido de reagendamento.
        await store.update_one("shipments", query, {"$set": {"reschedule_requested": True}})
        response = f"Reagendamento solicitado para o pedido {clean['order_id']}. A transportadora **{clean['carrier']}** vai confirmar uma nova janela de entrega em até 24h."
        event = TimelineEvent(category="agent", title="Reagendamento de entrega solicitado", agent="logistics_agent", collection="shipments", op="write", filter=query, result={**clean, "reschedule_requested": True}, duration_ms=(perf_counter() - started) * 1000)
        if wants_final_order_confirmation and order_already_ran:
            return AgentResult(response, event, "order_agent", "cliente pediu confirmação final do pedido após a etapa logística")
        return AgentResult(response, event)

    response = f"Pedido {clean['order_id']}: transportadora **{clean['carrier']}**, código **{clean['tracking_code']}**, {clean['current_location']}, previsão **{clean['estimated_delivery']}**."
    trivial = _is_trivial_lookup(message, order_id)
    synthesized = None if trivial else await llm_synthesize(llm, agent_doc, budget, message, clean, "O cliente pode perguntar qualquer coisa sobre transportadora, rastreio, localização ou previsão de entrega — responda com base no documento acima, nunca invente transportadora ou prazo." + scope_hint)
    title = "Consulta de logística" + (" (resposta sintetizada pelo modelo)" if synthesized else " (modo econômico, sem chamada ao modelo)" if trivial else "")
    event = TimelineEvent(category="agent", title=title, agent="logistics_agent", collection="shipments", op="read", filter=query, result=clean, duration_ms=(perf_counter() - started) * 1000)
    if wants_final_order_confirmation and order_already_ran:
        return AgentResult(synthesized or response, event, "order_agent", "cliente pediu confirmação final do pedido após a etapa logística")
    return AgentResult(synthesized or response, event)


def _weighted_score(relevance: float, rating: float, stock: int) -> float:
    """Relevância pesa mais, mas nota e disponibilidade desempatam — igual a um ranking real de e-commerce."""
    return round(0.55 * relevance + 0.30 * (rating / 5.0) + 0.15 * min(stock, 20) / 20.0, 4)


def _stem(word: str) -> str:
    """Singular/plural aproximado em pt-BR: 'fones' e 'fone' precisam casar na busca local."""
    if len(word) > 4 and word.endswith("oes"):
        return word[:-3] + "ao"
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def _local_rank(items: list[dict], query: str, fields: tuple[str, ...]) -> list[dict]:
    words = {_stem(word) for word in normalize(query).split() if len(word) > 2}
    scored = []
    for item in items:
        haystack_words = {_stem(word) for word in normalize(" ".join(str(item.get(field, "")) for field in fields)).split()}
        matches = len(words & haystack_words)
        relevance = matches / max(len(words), 1)
        weighted = _weighted_score(relevance, item.get("rating", 4.0), item.get("stock", 10))
        scored.append({**item, "local_score": matches, "weighted_score": weighted})
    scored.sort(key=lambda item: item["weighted_score"], reverse=True)
    return scored


NUMBER_WORDS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10}


def detect_category(message: str) -> str | None:
    normalized = normalize(message)
    words = {_stem(word) for word in normalized.split()}
    for keyword, category in CATEGORY_KEYWORDS.items():
        if keyword in words:
            return category
    return None


def parse_price_ceiling(message: str) -> float | None:
    """Extrai teto de preço tanto em dígitos (R$ 350) quanto por extenso (até mil reais, até dois mil)."""
    normalized = normalize(message)
    digit_prices = [float(value.replace(",", ".")) for value in re.findall(r"(?:r\$\s*)?(\d+[.,]?\d*)\s*(?:reais|mil)?", normalized) if value]
    word_match = re.search(r"\b(um|uma|dois|duas|tres|quatro|cinco|seis|sete|oito|nove|dez)?\s*mil\b", normalized)
    if word_match:
        multiplier = NUMBER_WORDS.get(word_match.group(1), 1)
        return float(multiplier * 1000)
    if digit_prices:
        return min(digit_prices)
    return None


async def search_products(store: DataStore, message: str, max_price: float | None = None, category: str | None = None) -> list[dict]:
    if not store.memory:
        vector_filter: dict[str, Any] = {"active": True}
        if max_price is not None:
            vector_filter["price"] = {"$lt": max_price}
        if category:
            vector_filter["category"] = category
        pipeline = [
            {"$vectorSearch": {"index": "products_autoembed_v1", "path": "search_text", "query": {"text": message}, "model": "voyage-4", "filter": vector_filter, "numCandidates": 50, "limit": 8}},
            {"$addFields": {"relevance": {"$meta": "vectorSearchScore"}}},
            {"$addFields": {"weighted_score": {"$add": [
                {"$multiply": [0.55, "$relevance"]},
                {"$multiply": [0.30, {"$divide": ["$rating", 5.0]}]},
                {"$multiply": [0.15, {"$divide": [{"$min": ["$stock", 20]}, 20.0]}]},
            ]}}},
            {"$sort": {"weighted_score": -1}},
            {"$limit": 4},
            {"$project": {"_id": 0, "sku": 1, "name": 1, "category": 1, "price": 1, "rating": 1, "stock": 1, "relevance": 1, "weighted_score": 1}},
        ]
        try:
            cursor = await store._collection("products_catalog").aggregate(pipeline)
            return await cursor.to_list(None)
        except Exception:
            pass
    products = await store.find_many("products_catalog", {"active": True}, limit=100)
    if category:
        products = [item for item in products if item["category"] == category]
    if max_price is not None:
        products = [item for item in products if item["price"] < max_price]
    return [public_document(item) for item in _local_rank(products, message, ("name", "category", "search_text"))[:4]]


async def run_product_agent(store: DataStore, message: str, customer: dict, llm=None, budget=None, agent_doc=None, scope_hint: str = "", context: dict | None = None) -> AgentResult:
    started = perf_counter()
    facts = await active_facts(store, customer["customer_key"])
    category = detect_category(message)
    explicit_price = parse_price_ceiling(message)
    memory_bias = "price_sensitive" in facts and explicit_price is None
    max_price = explicit_price if explicit_price is not None else (350.0 if ("mais barato" in normalize(message) or memory_bias) else None)
    products = await search_products(store, message, max_price, category)
    if not products and category:
        # teto de preço pode ter zerado a categoria certa; melhor mostrar algo da categoria do que nada.
        products = await search_products(store, message, None, category)
    if not products and not category:
        # pergunta totalmente fora do script (ex. "o que vocês têm de bom pra presentear alguém"): dá pro
        # modelo o catálogo inteiro ativo pra ele raciocinar, em vez de simplesmente desistir.
        products = [public_document(item) for item in _local_rank(await store.find_many("products_catalog", {"active": True}, limit=100), message, ("name", "category", "search_text"))[:6]]
    if products:
        lines = [f"- **{item['name']}** — R$ {item['price']:.2f} · ★{item.get('rating', '—')} · {item.get('stock', 0)} em estoque" for item in products[:3]]
        response = "Encontrei estas opções no catálogo:\n" + "\n".join(lines)
        if memory_bias:
            response += "\n\n(Levei em conta que você já demonstrou preferência por preços mais baixos.)"
    elif category:
        response = f"Não encontrei produtos ativos na categoria {category} dentro desse orçamento."
    else:
        response = "Não encontrei uma opção compatível no catálogo ativo."
    synthesized = await llm_synthesize(
        llm, agent_doc, budget, message, products,
        "Escolha e recomende só produtos desta lista (nunca invente um SKU/preço fora dela). Se nada da lista "
        "atender o pedido, diga honestamente e sugira o mais próximo disponível, explicando a diferença. Você "
        "é o agente de PRODUTOS: se a mensagem menciona um defeito, isso já foi tratado por outro agente antes "
        "de chegar até você — não pergunte de novo qual produto teve defeito, só recomende a alternativa.",
    )
    search_filter: dict[str, Any] = {"active": True}
    if category:
        search_filter["category"] = category
    if max_price is not None:
        search_filter["price"] = {"$lt": max_price}
    event = TimelineEvent(category="agent", title="Recomendação com ranking ponderado (relevância + nota + estoque)" + (" + modelo" if synthesized else ""), agent="product_agent", collection="products_catalog", op="vectorSearch", filter=search_filter, result=products[:3], duration_ms=(perf_counter() - started) * 1000)
    events = [event]
    if memory_bias:
        events.append(TimelineEvent(category="memory", title="Viés aplicado a partir da memória do cliente", agent="product_agent", collection="customer_memory", filter={"customer_key": customer["customer_key"], "fact_type": "price_sensitive"}, result={"fact": facts["price_sensitive"]}))
    final_response = synthesized or response
    # 3º hop da cadeia: cliente já pediu diagnóstico (support_agent) e recomendação (aqui) — se também confirmou
    # querer efetivar a troca, quem processa isso com segurança é o order_agent (única escrita do sistema).
    wants_to_act = products and any(term in normalize(message) for term in ("troca", "trocar", "reembolso", "reembolsar", "estornar"))
    if wants_to_act:
        return AgentResult(final_response, event, "order_agent", "cliente confirmou que quer efetivar a troca do produto recomendado", extra_events=events[1:])
    return AgentResult(final_response, event, extra_events=events[1:])


async def search_kb(store: DataStore, message: str) -> list[dict]:
    if not store.memory:
        vector_pipeline = [{"$vectorSearch": {"index": "kb_autoembed_v1", "path": "content", "query": {"text": message}, "model": "voyage-4", "numCandidates": 50, "limit": 10}}, {"$project": {"article_id": 1, "title": 1, "content": 1, "category": 1}}]
        lexical_pipeline = [{"$search": {"index": "kb_lexical_v1", "compound": {"should": [{"text": {"query": message, "path": "title", "score": {"boost": {"value": 2}}}}, {"text": {"query": message, "path": "content"}}], "minimumShouldMatch": 1}}}, {"$limit": 10}, {"$project": {"article_id": 1, "title": 1, "content": 1, "category": 1}}]
        try:
            async def execute(pipeline: list[dict]) -> list[dict]:
                cursor = await store._collection("kb_articles").aggregate(pipeline)
                return await cursor.to_list(None)
            vector, lexical = await asyncio.gather(execute(vector_pipeline), execute(lexical_pipeline))
            for item in vector + lexical:
                item["_id"] = item.get("article_id")
            return reciprocal_rank_fusion([vector, lexical], limit=4)
        except Exception:
            pass
    articles = await store.find_many("kb_articles", {}, limit=100)
    lexical = _local_rank(articles, message, ("title", "content"))
    semantic = _local_rank(articles, message, ("category", "title"))
    return reciprocal_rank_fusion([lexical, semantic], limit=4)


async def run_support_agent(store: DataStore, message: str, customer: dict, llm=None, budget=None, agent_doc=None, scope_hint: str = "", context: dict | None = None) -> AgentResult:
    started = perf_counter()
    articles = await search_kb(store, message)
    clean = [public_document(item) for item in articles]
    evidence = clean[0] if clean else None
    response = f"A orientação da base é: {evidence['content']}" if evidence else "Não encontrei orientação confiável na base de suporte."
    wants_recommendation = any(term in normalize(message) for term in ("parecido", "parecida", "similar", "mais barato", "mais barata", "recomenda"))
    handoff_note = (
        "O cliente também pediu uma recomendação de produto — você é o agente de SUPORTE, não tem o catálogo. "
        "NÃO diga que não tem acesso a preços/catálogo: diga em uma frase curta que vai conectar com o "
        "especialista em produtos, que ele já vai trazer as opções a seguir. Não repita o pedido de saber qual "
        "modelo foi comprado se o cliente já descreveu o produto na mensagem."
        if wants_recommendation else
        "Se nenhum artigo cobrir o problema relatado, diga que vai escalar/orientar de forma genérica em vez de inventar um passo a passo."
    )
    synthesized = await llm_synthesize(llm, agent_doc, budget, message, clean, handoff_note)
    event = TimelineEvent(category="agent", title="RAG híbrido com RRF" + (" + modelo" if synthesized else ""), agent="support_agent", collection="kb_articles", op="hybridSearch", filter={"query": message}, result=clean[:3], duration_ms=(perf_counter() - started) * 1000)
    final_response = synthesized or response
    extra_events: list[TimelineEvent] = []

    wants_escalation = any(term in normalize(message) for term in ("abrir chamado", "falar com humano", "escalar", "atendente", "chamado"))
    if wants_escalation:
        # KB sem evidência confiável (ou pedido explícito de escalonar): abre chamado real em vez de deixar
        # o cliente sem próximo passo — mais uma ação de escrita além do write único do order_agent.
        ticket = {"ticket_id": f"TCK-{customer['customer_key'].upper()}-{int(started * 1000) % 100000}", "customer_key": customer["customer_key"], "area": customer["area"], "subject": message[:200], "status": "aberto", "created_at": utcnow()}
        await store.insert_one("support_tickets", ticket)
        final_response += f"\n\nAbri o chamado **{ticket['ticket_id']}** para acompanhamento humano — nosso time entra em contato em até 24h."
        extra_events.append(TimelineEvent(category="agent", title="Chamado de suporte aberto", agent="support_agent", collection="support_tickets", op="write", result=ticket))

    if wants_recommendation:
        return AgentResult(final_response, event, "product_agent", "cliente pediu alternativa de produto após o diagnóstico", extra_events=extra_events)
    return AgentResult(final_response, event, extra_events=extra_events)


RUNNERS = {
    "order_agent": run_order_agent,
    "product_agent": run_product_agent,
    "support_agent": run_support_agent,
    "billing_agent": run_billing_agent,
    "warranty_agent": run_warranty_agent,
    "loyalty_agent": run_loyalty_agent,
    "logistics_agent": run_logistics_agent,
}
