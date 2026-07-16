from collections import defaultdict
from typing import Hashable


def reciprocal_rank_fusion(
    rankings: list[list[dict]], *, key: str = "_id", k: int = 60, limit: int = 5
) -> list[dict]:
    """Combina rankings lexical e vetorial sem comparar escalas de score."""
    scores: dict[Hashable, float] = defaultdict(float)
    documents: dict[Hashable, dict] = {}
    for ranking in rankings:
        for position, document in enumerate(ranking, start=1):
            document_key = document[key]
            documents[document_key] = document
            scores[document_key] += 1 / (k + position)
    ordered = sorted(scores, key=scores.get, reverse=True)[:limit]
    return [{**documents[item], "rrf_score": round(scores[item], 6)} for item in ordered]

