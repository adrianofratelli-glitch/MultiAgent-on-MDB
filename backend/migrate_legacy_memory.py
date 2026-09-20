"""Migra documentos legados de `customer_memory` (fact_type/value) para o formato do extrator (fact/...).

Aditivo e idempotente: só ACRESCENTA campos (`fact`, `fact_norm`, `category`, `superseded_by`,
`migrated_from`) e nunca remove `fact_type`/`value`, então dá para reverter. `price_sensitive` ganha
`max_price_brl = 350`: era exatamente o teto fixo que o product_agent antigo aplicava, então o
comportamento do cliente não muda — só passa a ser o campo estruturado que o servidor filtra.

    python migrate_legacy_memory.py           # dry-run: só conta
    python migrate_legacy_memory.py --apply   # grava
"""

import asyncio
import sys

from app.config import get_settings
from app.database import DataStore, utcnow
from app.memory import _fact_norm

LEGACY_PRICE_CAP_BRL = 350.0
CATEGORY_BY_TYPE = {"price_sensitive": "preferencia", "product_complaint": "historico"}


async def migrate(store: DataStore, *, apply: bool) -> int:
    """Devolve quantos documentos legados foram (ou seriam) migrados."""
    legacy = [d for d in await store.find_many("customer_memory", {"value": {"$exists": True}}, limit=10_000)
              if not d.get("fact")]
    if not apply:
        return len(legacy)
    for doc in legacy:
        update = {"fact": doc["value"], "fact_norm": _fact_norm(doc["value"]),
                  "category": CATEGORY_BY_TYPE.get(doc.get("fact_type"), "contexto"),
                  "superseded_by": None, "migrated_from": doc.get("fact_type"), "updated_at": utcnow()}
        if doc.get("fact_type") == "price_sensitive" and doc.get("active"):  # histórico inativo não ganha teto
            update["max_price_brl"] = LEGACY_PRICE_CAP_BRL
        await store.update_one("customer_memory", {"_id": doc["_id"]}, {"$set": update})
    return len(legacy)


async def main() -> None:
    apply = "--apply" in sys.argv
    store = DataStore(get_settings())
    await store.connect()
    try:
        if store.memory:
            sys.exit("DEMO_MODE/sem MONGODB_URI: nada a migrar.")
        count = await migrate(store, apply=apply)
        print(f"{'migrados' if apply else 'seriam migrados (dry-run)'}: {count} documento(s)")
    finally:
        await store.close()


if __name__ == "__main__":
    asyncio.run(main())
