from dataclasses import dataclass, field
from datetime import timedelta
from typing import Literal

from .budget import estimate_tokens
from .config import get_settings
from .database import DataStore, utcnow
from .router import normalize

# Só conteúdo de catálogo/KB pode sequer ser candidato a cache cross-customer. A decisão final também exige
# ``global_eligible=True`` do orquestrador, depois de confirmar que o turno não usou memória do cliente, não
# teve handoff e não escreveu nada. Intenção isolada não prova que a resposta é pública.
GLOBAL_CACHE_INTENTS = frozenset({"recomendacao", "produto_similar", "suporte", "defeito"})


@dataclass
class CascadeResult:
    hit: bool
    fonte: Literal["curto_prazo", "cache"] | None = None
    score: float | None = None
    answer: str | None = None
    active_agent: str | None = None
    timeline: list[dict] = field(default_factory=list)
    tokens_economizados: int = 0


async def cascade_lookup(store: DataStore, *, target: str, area: str, customer_key: str, session_id: str, message: str) -> CascadeResult:
    """UMA consulta decide HIT/MISS antes do LLM: $vectorSearch em curto_prazo (filtrado por sessão, threshold
    permissivo — pega reformulação) $unionWith $vectorSearch em cache (sem filtro de sessão, threshold rígido —
    pergunta comum já respondida), cada ramo já filtrado pelo próprio threshold ANTES do union, senão um score
    de cache abaixo do seu threshold rígido podia vencer o sort só por ser maior que o corte do curto_prazo."""
    settings = get_settings()
    if store.memory:
        return await _cascade_lookup_fallback(store, target=target, area=area, customer_key=customer_key, session_id=session_id, message=message)

    pipeline = [
        {"$vectorSearch": {"index": "short_term_autoembed_v1", "path": "question_text", "query": {"text": message}, "model": "voyage-4", "filter": {"session_id": session_id, "customer_key": customer_key, "agent": target}, "numCandidates": 50, "limit": 5}},
        {"$addFields": {"score": {"$meta": "vectorSearchScore"}, "fonte": "curto_prazo"}},
        {"$match": {"score": {"$gte": settings.short_term_cache_threshold}}},
        {"$sort": {"score": -1}},
        {"$limit": 1},
        {
            "$unionWith": {
                "coll": "semantic_cache",
                "pipeline": [
                    {"$vectorSearch": {"index": "cache_autoembed_v1", "path": "question_text", "query": {"text": message}, "model": "voyage-4", "filter": {"$or": [{"scope": "global", "area": area, "agent": target}, {"scope": "customer", "customer_key": customer_key, "agent": target}]}, "numCandidates": 50, "limit": 5}},
                    {"$addFields": {"score": {"$meta": "vectorSearchScore"}, "fonte": "cache"}},
                    {"$match": {"score": {"$gte": settings.global_cache_threshold}}},
                    {"$sort": {"score": -1}},
                    {"$limit": 1},
                ],
            }
        },
        {"$sort": {"score": -1}},
        {"$limit": 1},
    ]
    results = await store.aggregate("short_term_memory", pipeline)
    if not results:
        return CascadeResult(hit=False)
    best = results[0]
    tokens = estimate_tokens(best.get("answer", ""))
    return CascadeResult(
        hit=True,
        fonte=best["fonte"],
        score=best["score"],
        answer=best.get("answer"),
        active_agent=best.get("active_agent", target),
        timeline=best.get("timeline", []),
        tokens_economizados=tokens,
    )


async def _cascade_lookup_fallback(store: DataStore, *, target: str, area: str, customer_key: str, session_id: str, message: str) -> CascadeResult:
    """DEMO_MODE não tem índice de vetor real — sem embedding local pra simular cosine similarity, o HIT vira
    match exato de question_norm (mesmo contrato hit/fonte/score que o caminho real, score fixo em 1.0).
    Mantém curto_prazo antes de cache, mesma prioridade do caminho com Atlas."""
    question_norm = normalize(message)
    short = await store.find_one("short_term_memory", {"session_id": session_id, "customer_key": customer_key, "agent": target, "question_norm": question_norm, "expires_at": {"$gt": utcnow()}})
    if short:
        return CascadeResult(hit=True, fonte="curto_prazo", score=1.0, answer=short.get("answer"), active_agent=short.get("active_agent", target), timeline=short.get("timeline", []), tokens_economizados=estimate_tokens(short.get("answer", "")))
    cached = await store.find_one("semantic_cache", {"agent": target, "customer_key": customer_key, "scope": "customer", "question_norm": question_norm, "expires_at": {"$gt": utcnow()}})
    if not cached:
        cached = await store.find_one("semantic_cache", {"agent": target, "area": area, "scope": "global", "question_norm": question_norm, "expires_at": {"$gt": utcnow()}})
    if cached:
        return CascadeResult(hit=True, fonte="cache", score=1.0, answer=cached.get("answer"), active_agent=cached.get("active_agent", target), timeline=cached.get("timeline", []), tokens_economizados=estimate_tokens(cached.get("answer", "")))
    return CascadeResult(hit=False)


async def cascade_long_term_context(store: DataStore, *, customer_key: str, message: str) -> list[dict]:
    """MISS nos dois: puxa contexto de longo prazo (memória semântica/episódica do cliente) pro prompt —
    isso NÃO é resposta pronta, é input do LLM, por isso não conta como cache hit."""
    settings = get_settings()
    if store.memory:
        return await store.find_many("long_term_memory", {"customer_key": customer_key}, limit=settings.long_term_memory_limit)
    pipeline = [
        {"$vectorSearch": {"index": "long_term_autoembed_v1", "path": "text", "query": {"text": message}, "model": "voyage-4", "filter": {"customer_key": customer_key}, "numCandidates": 50, "limit": settings.long_term_memory_limit}},
        {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
    ]
    return await store.aggregate("long_term_memory", pipeline)


async def cascade_store_turn(
    store: DataStore,
    *,
    target: str,
    area: str,
    customer_key: str,
    session_id: str,
    intent: str | None,
    message: str,
    answer: str,
    timeline: list[dict],
    active_agent: str,
    global_eligible: bool = False,
) -> None:
    """Grava sempre em curto_prazo (essa sessão pode reformular a pergunta no próximo turno) e sempre em
    cache com scope="customer" (mesmo cliente, sem depender da sessão continuar — cobre repetir a mesma
    pergunta numa conversa nova). Só grava TAMBÉM com scope="global" quando intenção E evidências do turno
    provam que a resposta é pública; o caller precisa optar explicitamente por esse compartilhamento."""
    question_norm = normalize(message)
    now = utcnow()
    await store.replace_one(
        "short_term_memory",
        {"session_id": session_id, "customer_key": customer_key, "agent": target, "question_norm": question_norm},
        {"session_id": session_id, "agent": target, "area": area, "customer_key": customer_key, "question_text": message, "question_norm": question_norm, "answer": answer, "active_agent": active_agent, "timeline": timeline, "created_at": now, "expires_at": now + timedelta(hours=24)},
        upsert=True,
    )
    await store.replace_one(
        "semantic_cache",
        {"agent": target, "customer_key": customer_key, "scope": "customer", "question_norm": question_norm},
        {"agent": target, "area": area, "customer_key": customer_key, "scope": "customer", "question_text": message, "question_norm": question_norm, "answer": answer, "active_agent": active_agent, "timeline": timeline, "created_at": now, "expires_at": now + timedelta(minutes=60)},
        upsert=True,
    )
    if global_eligible and intent in GLOBAL_CACHE_INTENTS:
        await store.replace_one(
            "semantic_cache",
            {"agent": target, "area": area, "scope": "global", "question_norm": question_norm},
            {"agent": target, "area": area, "scope": "global", "question_text": message, "question_norm": question_norm, "answer": answer, "active_agent": active_agent, "timeline": timeline, "created_at": now, "expires_at": now + timedelta(minutes=60)},
            upsert=True,
        )
