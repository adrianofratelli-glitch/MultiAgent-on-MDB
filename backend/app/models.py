from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class TokenRequest(BaseModel):
    customer_key: str = Field(min_length=3, max_length=64)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, max_length=80)


class AgentUpdate(BaseModel):
    active: bool | None = None
    model: str | None = Field(default=None, max_length=100)
    fallback_model: str | None = Field(default=None, max_length=100)
    persona: str | None = Field(default=None, max_length=4000)
    max_turn_tokens: int | None = Field(default=None, ge=128, le=8192)


class OrderStatusUpdate(BaseModel):
    order_id: str
    status: Literal["processando", "enviado", "entregue", "troca_solicitada", "reembolsado"]

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, value: str) -> str:
        value = value.upper().strip()
        if not value.startswith("PED-") or not value[4:].isdigit():
            raise ValueError("order_id deve seguir o formato PED-0000")
        return value


class TimelineEvent(BaseModel):
    category: Literal["agent", "memory", "guardrail", "cache", "handoff", "fanout"]
    title: str
    agent: str | None = None
    collection: str | None = None
    op: Literal["read", "write", "vectorSearch", "hybridSearch", "changeStream"] | None = None
    filter: dict[str, Any] | None = None
    result: Any = None
    reason: str | None = None
    duration_ms: float = 0


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    active_agent: str
    route_source: Literal["rules", "orchestrator", "fallback", "fanout"]
    cache_hit: bool
    cache_source: Literal["curto_prazo", "cache"] | None = None
    tokens_economizados: int = 0
    timeline: list[TimelineEvent]
    usage: dict[str, int]

