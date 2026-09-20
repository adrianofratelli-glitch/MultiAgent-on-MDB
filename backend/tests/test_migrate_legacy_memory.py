from app.config import Settings
from app.database import DataStore, utcnow
from app.memory import active_budget, active_facts
from migrate_legacy_memory import LEGACY_PRICE_CAP_BRL, migrate


async def legacy_store():
    store = DataStore(Settings(demo_mode=True))
    for key, ftype, value in (("bruno", "price_sensitive", "Cliente sensível a preço"),
                              ("bruno", "product_complaint", "Cliente relatou defeito"),
                              ("ana", "price_sensitive", "Cliente sensível a preço")):
        await store.insert_one("customer_memory", {"customer_key": key, "fact_type": ftype, "value": value, "active": True, "created_at": utcnow()})
    await store.insert_one("customer_memory", {"customer_key": "carla", "fact": "novo", "fact_norm": "novo", "category": "preferencia", "active": True, "created_at": utcnow()})
    return store


async def test_dry_run_changes_nothing():
    store = await legacy_store()
    assert await migrate(store, apply=False) == 3
    assert await active_budget(store, "bruno") is None


async def test_apply_preserves_old_behaviour_and_keeps_legacy_fields():
    store = await legacy_store()
    assert await migrate(store, apply=True) == 3
    assert await active_budget(store, "bruno") == LEGACY_PRICE_CAP_BRL == 350.0  # o teto que o product_agent antigo aplicava
    assert await active_budget(store, "carla") is None
    docs = await store.find_many("customer_memory", {"customer_key": "bruno"})
    complaint = next(d for d in docs if d["fact_type"] == "product_complaint")
    assert complaint["fact"] == "Cliente relatou defeito" and "max_price_brl" not in complaint and complaint["value"]
    assert len(await active_facts(store, "bruno")) == 2


async def test_apply_is_idempotent():
    store = await legacy_store()
    await migrate(store, apply=True)
    assert await migrate(store, apply=True) == 0
