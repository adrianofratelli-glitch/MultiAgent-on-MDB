from app.agents import semantic_cache_get, semantic_cache_put
from app.config import Settings
from app.database import DataStore


async def test_cache_does_not_leak_between_customers_in_same_area():
    store = DataStore(Settings(demo_mode=True))
    await semantic_cache_put(store, "order_agent", "varejo", "ana", "pedido 1", "resposta da Ana", [])
    assert await semantic_cache_get(store, "order_agent", "varejo", "ana", "pedido 1")
    assert await semantic_cache_get(store, "order_agent", "varejo", "bruno", "pedido 1") is None
