from functools import lru_cache
from typing import Any

from .config import Settings, get_settings


class _NoopLangfuse:
    """Sem chave configurada: instrumentação vira no-op, igual ao padrão de fallback do resto do repo
    (LLMGateway sem api key, guardrail sem client) — DEMO_MODE/CI não dependem de credencial externa."""

    def trace(self, **kwargs) -> "_NoopTrace":
        return _NoopTrace()


class _NoopTrace:
    def span(self, **kwargs) -> None:
        return None

    def generation(self, **kwargs) -> None:
        return None

    def update(self, **kwargs) -> None:
        return None


@lru_cache
def get_langfuse(settings: Settings | None = None) -> Any:
    settings = settings or get_settings()
    if not settings.langfuse_enabled:
        return _NoopLangfuse()
    from langfuse import Langfuse

    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


def log_cache_decision(
    *,
    conversation_id: str,
    customer_key: str,
    message: str,
    cache: str,
    fonte: str | None,
    score: float | None,
    tokens_economizados: int,
    memorias_recuperadas: int,
    response: str | None = None,
    usage: dict | None = None,
    model: str | None = None,
) -> None:
    """Um trace por turno de decisão de cache: span pro HIT (sem chamada de LLM), generation pro MISS
    (LLM foi chamado de verdade). Estimativa de tokens economizados é sempre rotulada como estimativa,
    não como medição real de uso — só o MISS carrega usage real vindo do budget."""
    client = get_langfuse()
    trace = client.trace(name="semantic_cache_cascade", session_id=conversation_id, user_id=customer_key, input=message)
    if cache == "hit":
        trace.span(
            name="cache_lookup",
            input=message,
            output=response,
            metadata={"cache": "hit", "fonte": fonte, "score": score, "tokens_economizados_estimado": tokens_economizados},
        )
    else:
        trace.generation(
            name="llm_synthesize",
            input=message,
            output=response,
            model=model,
            usage=usage,
            metadata={"cache": "miss", "memorias_recuperadas": memorias_recuperadas},
        )
