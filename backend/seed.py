"""Seed idempotente do plano de dados e do plano de coordenação."""

import asyncio
import sys
from pathlib import Path

from pymongo.operations import SearchIndexModel

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import get_settings  # noqa: E402
from app.database import DataStore  # noqa: E402
from app.seed_data import (  # noqa: E402
    AGENTS,
    DEMO_SCENARIOS,
    GUARDRAIL_POLICIES,
    ROUTING_RULES,
    seed_documents,
)


KEYS = {
    "customers": "customer_key",
    "orders": "order_id",
    "invoices": "invoice_id",
    "products_catalog": "sku",
    "kb_articles": "article_id",
    "warranty_policies": "category",
    "loyalty_accounts": "customer_key",
    "shipments": "order_id",
    "guardrail_denylist": "phrase_norm",
    "semantic_cache": "question_norm",
}


async def seed(store: DataStore, *, create_indexes: bool = True) -> list[str]:
    messages: list[str] = []
    for collection, documents in seed_documents().items():
        key = KEYS[collection]
        for document in documents:
            await store.replace_one(collection, {key: document[key]}, document, upsert=True)
        messages.append(f"{collection}: {len(documents)} documentos")

    for agent in AGENTS:
        await store.replace_one(
            "agent_registry", {"agent_key": agent["agent_key"]}, agent, brain=True, upsert=True
        )
    messages.append(f"agent_registry: {len(AGENTS)} agentes, todos reais")
    for rule in ROUTING_RULES:
        await store.replace_one(
            "routing_rules", {"intent": rule["intent"]}, rule, brain=True, upsert=True
        )
    for scenario in DEMO_SCENARIOS:
        await store.replace_one(
            "demo_scenarios", {"scenario_id": scenario["scenario_id"]}, scenario, brain=True, upsert=True
        )
    for policy in GUARDRAIL_POLICIES:
        await store.replace_one(
            "guardrail_policies", {"area": policy["area"]}, policy, brain=True, upsert=True
        )
    await store.replace_one(
        "model_config",
        {"key": "default"},
        {"key": "default", "default_model": "claude-haiku-4-5", "global_turn_tokens": 6000},
        brain=True,
        upsert=True,
    )
    messages.append(f"ai_brain: registry, routing, policies, model_config e {len(DEMO_SCENARIOS)} cenários")

    if create_indexes:
        try:
            await store.create_standard_indexes()
            messages.append("índices B-tree, únicos e TTL: prontos")
        except Exception as exc:  # índice existente com outra definição ou permissão limitada
            messages.append(f"índices padrão: aviso ({exc})")
        messages.extend(await store.create_schema_validators())
        messages.extend(await create_search_indexes(store))
    return messages


async def create_search_indexes(store: DataStore) -> list[str]:
    if store.memory:
        return ["índices Search/Vector: ignorados em DEMO_MODE"]
    definitions = [
        (
            "products_catalog",
            SearchIndexModel(
                name="products_autoembed_v1",
                type="vectorSearch",
                definition={
                    "fields": [
                        {"type": "autoEmbed", "modality": "text", "path": "search_text", "model": "voyage-4", "numDimensions": 1024, "similarity": "cosine", "indexingMethod": "flat"},
                        {"type": "filter", "path": "category"},
                        {"type": "filter", "path": "active"},
                        {"type": "filter", "path": "price"},
                    ]
                },
            ),
        ),
        (
            "kb_articles",
            SearchIndexModel(
                name="kb_autoembed_v1",
                type="vectorSearch",
                definition={
                    "fields": [
                        {"type": "autoEmbed", "modality": "text", "path": "content", "model": "voyage-4", "numDimensions": 1024, "similarity": "cosine", "indexingMethod": "flat"},
                        {"type": "filter", "path": "category"},
                    ]
                },
            ),
        ),
        (
            "kb_articles",
            SearchIndexModel(
                name="kb_lexical_v1",
                definition={"mappings": {"dynamic": False, "fields": {"title": {"type": "string", "analyzer": "lucene.portuguese"}, "content": {"type": "string", "analyzer": "lucene.portuguese"}, "category": {"type": "token"}}}},
            ),
        ),
        (
            "customer_memory",
            SearchIndexModel(
                name="memory_autoembed_v1",
                type="vectorSearch",
                definition={"fields": [{"type": "autoEmbed", "modality": "text", "path": "fact", "model": "voyage-4", "numDimensions": 1024, "similarity": "cosine", "indexingMethod": "flat"}, {"type": "filter", "path": "customer_key"}, {"type": "filter", "path": "active"}]},
            ),
        ),
        (
            "semantic_cache",
            SearchIndexModel(
                name="cache_autoembed_v1",
                type="vectorSearch",
                definition={"fields": [{"type": "autoEmbed", "modality": "text", "path": "question_text", "model": "voyage-4", "numDimensions": 1024, "similarity": "cosine", "indexingMethod": "flat"}, {"type": "filter", "path": "agent"}, {"type": "filter", "path": "area"}, {"type": "filter", "path": "customer_key"}, {"type": "filter", "path": "scope"}]},
            ),
        ),
        (
            "short_term_memory",
            SearchIndexModel(
                name="short_term_autoembed_v1",
                type="vectorSearch",
                definition={"fields": [{"type": "autoEmbed", "modality": "text", "path": "question_text", "model": "voyage-4", "numDimensions": 1024, "similarity": "cosine", "indexingMethod": "flat"}, {"type": "filter", "path": "session_id"}, {"type": "filter", "path": "customer_key"}, {"type": "filter", "path": "agent"}]},
            ),
        ),
        (
            "long_term_memory",
            SearchIndexModel(
                name="long_term_autoembed_v1",
                type="vectorSearch",
                definition={"fields": [{"type": "autoEmbed", "modality": "text", "path": "text", "model": "voyage-4", "numDimensions": 1024, "similarity": "cosine", "indexingMethod": "flat"}, {"type": "filter", "path": "customer_key"}]},
            ),
        ),
    ]
    messages: list[str] = []
    for collection, model in definitions:
        try:
            db = store.client[store.settings.mongodb_db]
            try:
                await db.create_collection(collection)
            except Exception:
                pass  # já existe
            cursor = await store._collection(collection).list_search_indexes()
            existing = {item["name"] for item in await cursor.to_list(None)}
            if model.document["name"] not in existing:
                await store._collection(collection).create_search_index(model)
            else:
                await store._collection(collection).update_search_index(
                    model.document["name"],
                    model.document["definition"],
                )
            messages.append(f"{collection}.{model.document['name']}: solicitado")
        except Exception as exc:
            messages.append(f"{collection}.{model.document['name']}: best-effort ({exc})")
    return messages


async def main() -> None:
    store = DataStore(get_settings())
    await store.connect()
    try:
        for message in await seed(store):
            print(f"[seed] {message}")
    finally:
        await store.close()


if __name__ == "__main__":
    asyncio.run(main())
