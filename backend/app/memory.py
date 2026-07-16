from .database import DataStore, utcnow
from .router import normalize

PRICE_SENSITIVE_TERMS = ("mais barato", "mais em conta", "econômico", "economico", "caro demais", "promoção", "promocao")
DEFECT_TERMS = ("defeito", "quebrado", "não funciona", "nao funciona", "veio com problema")


async def extract_and_store(store: DataStore, customer_key: str, message: str) -> dict[str, str]:
    """Lê o turno, extrai fatos simples e faz supersessão transacional por fact_type."""
    normalized = normalize(message)
    written: dict[str, str] = {}
    if any(term in normalized for term in PRICE_SENSITIVE_TERMS):
        written["price_sensitive"] = await _upsert_fact(store, customer_key, "price_sensitive", "Cliente demonstrou sensibilidade a preço; priorizar opções mais baratas.")
    if any(term in normalized for term in DEFECT_TERMS):
        written["product_complaint"] = await _upsert_fact(store, customer_key, "product_complaint", "Cliente relatou defeito em um produto recebido; considerar histórico de qualidade ao recomendar.")
    return written


async def _upsert_fact(store: DataStore, customer_key: str, fact_type: str, value: str) -> str:
    existing = await store.find_many("customer_memory", {"customer_key": customer_key, "fact_type": fact_type, "active": True}, limit=10)
    for fact in existing:
        await store.update_one("customer_memory", {"_id": fact["_id"]}, {"$set": {"active": False, "superseded_at": utcnow()}})
    await store.insert_one("customer_memory", {"customer_key": customer_key, "fact_type": fact_type, "value": value, "active": True, "created_at": utcnow()})
    return value


async def active_facts(store: DataStore, customer_key: str) -> dict[str, str]:
    docs = await store.find_many("customer_memory", {"customer_key": customer_key, "active": True}, limit=20)
    return {doc["fact_type"]: doc["value"] for doc in docs}
