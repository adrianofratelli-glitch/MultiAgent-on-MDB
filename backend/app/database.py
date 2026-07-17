import asyncio
import copy
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, AsyncMongoClient

from .config import Settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _matches(document: dict, query: dict) -> bool:
    for key, expected in query.items():
        actual = document.get(key)
        if isinstance(expected, dict):
            for operator, value in expected.items():
                if operator == "$gt" and not actual > value:
                    return False
                if operator == "$gte" and not actual >= value:
                    return False
                if operator == "$lt" and not actual < value:
                    return False
                if operator == "$lte" and not actual <= value:
                    return False
                if operator == "$in" and actual not in value:
                    return False
                if operator == "$ne" and actual == value:
                    return False
                if operator == "$regex" and not (isinstance(actual, str) and re.search(value, actual)):
                    return False
        elif actual != expected:
            return False
    return True


class DataStore:
    """Uma porta pequena para Atlas com fallback determinístico para testes locais."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.memory = settings.use_memory_store
        self.client: AsyncMongoClient | None = None
        self._data: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        if self.memory:
            return
        self.client = AsyncMongoClient(
            self.settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            appname=self.settings.app_name,
        )
        await self.client.admin.command("ping")

    async def close(self) -> None:
        if self.client:
            await self.client.close()

    def _collection(self, name: str, brain: bool = False):
        if not self.client:
            raise RuntimeError("cliente MongoDB não conectado")
        db_name = self.settings.mongodb_brain_db if brain else self.settings.mongodb_db
        return self.client[db_name][name]

    def _bucket(self, name: str, brain: bool = False) -> list[dict]:
        db_name = self.settings.mongodb_brain_db if brain else self.settings.mongodb_db
        return self._data[db_name][name]

    async def ping(self) -> bool:
        if self.memory:
            return True
        await self.client.admin.command("ping")  # type: ignore[union-attr]
        return True

    async def find_one(self, name: str, query: dict, *, brain: bool = False) -> dict | None:
        if not self.memory:
            return await self._collection(name, brain).find_one(query)
        async with self._lock:
            return next((copy.deepcopy(d) for d in self._bucket(name, brain) if _matches(d, query)), None)

    async def find_many(
        self,
        name: str,
        query: dict | None = None,
        *,
        brain: bool = False,
        limit: int = 100,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[dict]:
        query = query or {}
        if not self.memory:
            cursor = self._collection(name, brain).find(query)
            if sort:
                cursor = cursor.sort(sort)
            return await cursor.to_list(length=limit)
        async with self._lock:
            items = [copy.deepcopy(d) for d in self._bucket(name, brain) if _matches(d, query)]
        if sort:
            for field, direction in reversed(sort):
                items.sort(key=lambda item: item.get(field) or datetime.min.replace(tzinfo=timezone.utc), reverse=direction < 0)
        return items[:limit]

    async def count(self, name: str, query: dict | None = None, *, brain: bool = False) -> int:
        if not self.memory:
            return await self._collection(name, brain).count_documents(query or {})
        return len(await self.find_many(name, query, brain=brain, limit=100_000))

    async def insert_one(self, name: str, document: dict, *, brain: bool = False) -> None:
        payload = copy.deepcopy(document)
        if not self.memory:
            await self._collection(name, brain).insert_one(payload)
            return
        async with self._lock:
            payload.setdefault("_id", f"{name}-{len(self._bucket(name, brain)) + 1}")
            self._bucket(name, brain).append(payload)

    async def replace_one(
        self, name: str, query: dict, document: dict, *, brain: bool = False, upsert: bool = False
    ) -> None:
        payload = copy.deepcopy(document)
        if not self.memory:
            await self._collection(name, brain).replace_one(query, payload, upsert=upsert)
            return
        async with self._lock:
            bucket = self._bucket(name, brain)
            for index, item in enumerate(bucket):
                if _matches(item, query):
                    payload.setdefault("_id", item.get("_id"))
                    bucket[index] = payload
                    return
            if upsert:
                payload.setdefault("_id", f"{name}-{len(bucket) + 1}")
                bucket.append(payload)

    async def update_one(
        self, name: str, query: dict, update: dict, *, brain: bool = False, upsert: bool = False
    ) -> int:
        if not self.memory:
            result = await self._collection(name, brain).update_one(query, update, upsert=upsert)
            return result.modified_count
        async with self._lock:
            bucket = self._bucket(name, brain)
            target = next((item for item in bucket if _matches(item, query)), None)
            if target is None and upsert:
                target = {**query, "_id": f"{name}-{len(bucket) + 1}"}
                bucket.append(target)
            if target is None:
                return 0
            for key, value in update.get("$set", {}).items():
                target[key] = copy.deepcopy(value)
            for key, value in update.get("$inc", {}).items():
                target[key] = target.get(key, 0) + value
            for key, value in update.get("$push", {}).items():
                target.setdefault(key, []).append(copy.deepcopy(value))
            return 1

    async def aggregate(self, name: str, pipeline: list[dict], *, brain: bool = False) -> list[dict]:
        """Só para pipelines reais ($vectorSearch/$unionWith) — sem equivalente em DEMO_MODE, chamador
        precisa ter um caminho alternativo quando self.memory é True (ver cascade.py)."""
        if self.memory:
            raise RuntimeError("aggregate() não tem fallback em DEMO_MODE — trate store.memory antes de chamar")
        cursor = await self._collection(name, brain).aggregate(pipeline)
        return await cursor.to_list(length=None)

    async def delete_many(self, name: str, query: dict, *, brain: bool = False) -> int:
        if not self.memory:
            result = await self._collection(name, brain).delete_many(query)
            return result.deleted_count
        async with self._lock:
            bucket = self._bucket(name, brain)
            kept = [item for item in bucket if not _matches(item, query)]
            deleted = len(bucket) - len(kept)
            bucket[:] = kept
            return deleted

    async def watch_handoffs(self, customer_key: str):
        """Live feed de handoffs do cliente: Change Stream no Atlas, poll no modo DEMO_MODE."""
        if not self.memory:
            try:
                async with self._collection("agent_handoffs").watch(
                    [{"$match": {"operationType": "insert"}}], full_document="updateLookup"
                ) as stream:
                    async for change in stream:
                        doc = change["fullDocument"]
                        owner = await self.find_one("agent_conversations", {"conversation_id": doc.get("conversation_id"), "customer_key": customer_key})
                        if owner:
                            yield {key: value for key, value in doc.items() if key != "_id"}
                return
            except Exception:
                pass
        seen: set[str] = set()
        while True:
            await asyncio.sleep(1.2)
            items = await self.find_many("agent_handoffs", {}, limit=200, sort=[("at", 1)])
            for item in items:
                marker = str(item.get("_id"))
                if marker in seen:
                    continue
                seen.add(marker)
                owner = await self.find_one("agent_conversations", {"conversation_id": item.get("conversation_id"), "customer_key": customer_key})
                if owner:
                    yield {key: value for key, value in item.items() if key != "_id"}

    async def create_schema_validators(self) -> list[str]:
        """Schema-at-boundary: cada handoff/trace é validado pelo próprio MongoDB, não só pela camada Python —
        o mesmo controle que arquiteturas AWS multi-agent pedem serviço externo (schema registry) pra garantir."""
        if self.memory:
            return ["JSON Schema validators: ignorados em DEMO_MODE"]
        validators = {
            "agent_handoffs": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["conversation_id", "from_agent", "to_agent", "reason", "at"],
                    "properties": {
                        "conversation_id": {"bsonType": "string", "minLength": 4},
                        "from_agent": {"bsonType": "string"},
                        "to_agent": {"bsonType": "string"},
                        "reason": {"bsonType": ["string", "null"]},
                        "at": {"bsonType": "date"},
                    },
                }
            },
            "agent_traces": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["conversation_id", "customer_key", "active_agent", "at"],
                    "properties": {
                        "conversation_id": {"bsonType": "string"},
                        "customer_key": {"bsonType": "string"},
                        "active_agent": {"bsonType": "string"},
                        "at": {"bsonType": "date"},
                    },
                }
            },
        }
        messages: list[str] = []
        db = self.client[self.settings.mongodb_db]
        for collection, validator in validators.items():
            try:
                await db.command("collMod", collection, validator=validator, validationLevel="moderate", validationAction="error")
                messages.append(f"{collection}: validator aplicado (collMod)")
            except Exception:
                try:
                    await db.create_collection(collection, validator=validator, validationLevel="moderate", validationAction="error")
                    messages.append(f"{collection}: validator aplicado (create_collection)")
                except Exception as exc:
                    messages.append(f"{collection}: validator best-effort ({exc})")
        return messages

    async def create_standard_indexes(self) -> None:
        if self.memory:
            return
        definitions = {
            "customers": [[("customer_key", ASCENDING)]],
            "orders": [[("order_id", ASCENDING)], [("owner_customer_key", ASCENDING), ("status", ASCENDING)]],
            "invoices": [[("invoice_id", ASCENDING)], [("owner_customer_key", ASCENDING), ("due_date", ASCENDING)]],
            "loyalty_accounts": [[("customer_key", ASCENDING)]],
            "shipments": [[("order_id", ASCENDING)], [("owner_customer_key", ASCENDING)]],
            "warranty_policies": [[("category", ASCENDING)]],
            "agent_conversations": [[("conversation_id", ASCENDING)], [("updated_at", ASCENDING)]],
            "customer_memory": [[("customer_key", ASCENDING), ("active", ASCENDING)]],
            "agent_handoffs": [[("conversation_id", ASCENDING), ("at", ASCENDING)], [("at", ASCENDING)]],
            "agent_traces": [[("conversation_id", ASCENDING), ("at", ASCENDING)], [("at", ASCENDING)]],
            "semantic_cache": [[("agent", ASCENDING), ("area", ASCENDING)], [("expires_at", ASCENDING)]],
            "short_term_memory": [[("session_id", ASCENDING)], [("expires_at", ASCENDING)]],
            "long_term_memory": [[("customer_key", ASCENDING)]],
            "guardrail_denylist": [[("phrase_norm", ASCENDING)]],
            "guardrail_events": [[("at", ASCENDING)]],
            "guardrail_candidates": [[("status", ASCENDING), ("created_at", ASCENDING)]],
            "admin_audit": [[("at", ASCENDING)]],
            "eval_runs": [[("at", ASCENDING)]],
            "support_tickets": [[("customer_key", ASCENDING), ("created_at", ASCENDING)]],
            "redemptions": [[("customer_key", ASCENDING), ("at", ASCENDING)]],
        }
        unique = {("customers", 0), ("orders", 0), ("invoices", 0), ("agent_conversations", 0), ("guardrail_denylist", 0), ("loyalty_accounts", 0), ("shipments", 0), ("warranty_policies", 0)}
        ttl = {
            ("agent_conversations", 1): 86400,
            ("agent_handoffs", 1): 30 * 86400,
            ("agent_traces", 1): 30 * 86400,
            ("semantic_cache", 1): 0,
            ("short_term_memory", 1): 0,
            ("guardrail_events", 0): 30 * 86400,
            ("admin_audit", 0): 30 * 86400,
            ("eval_runs", 0): 90 * 86400,
        }
        for collection, indexes in definitions.items():
            for position, keys in enumerate(indexes):
                options: dict[str, Any] = {}
                if (collection, position) in unique:
                    options["unique"] = True
                if (collection, position) in ttl:
                    options["expireAfterSeconds"] = ttl[(collection, position)]
                await self._collection(collection).create_index(keys, **options)


store: DataStore | None = None


def set_store(value: DataStore) -> None:
    global store
    store = value


def get_store() -> DataStore:
    if store is None:
        raise RuntimeError("DataStore ainda não inicializado")
    return store

