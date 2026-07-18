import asyncio

import anthropic

from .budget import TurnBudget, estimate_tokens
from .config import Settings


class LLMGateway:
    """Gateway Anthropic com retry transitório, fallback e prompt cache."""

    def __init__(self, settings: Settings):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, default_headers={"api-key": settings.anthropic_api_key}) if settings.anthropic_api_key else None

    async def complete(
        self,
        *,
        agent: dict,
        user_message: str,
        dynamic_context: str,
        budget: TurnBudget,
        static_context: str = "",
    ) -> tuple[str | None, dict[str, int]]:
        if not self.client:
            return None, {"input_tokens": 0, "output_tokens": 0}
        # static_context (regras de grounding, idênticas em todo turno) entra no
        # MESMO bloco cacheável da persona: juntos passam do mínimo de 1024
        # tokens que o Anthropic exige para efetivar o prompt cache — persona
        # sozinha ficava abaixo e o cache_control era um no-op.
        system_static = agent["persona"] + (f"\n\n{static_context}" if static_context else "")
        estimated = estimate_tokens(system_static + user_message + dynamic_context)
        budget.reserve(agent["agent_key"], estimated)
        models = [agent["model"]]
        if agent.get("fallback_model") and agent["fallback_model"] not in models:
            models.append(agent["fallback_model"])
        last_error: Exception | None = None
        for model in models:
            for attempt in range(3):
                try:
                    response = await self.client.messages.create(
                        model=model,
                        max_tokens=min(agent["max_turn_tokens"], budget.global_limit - budget.total_used),
                        system=[{"type": "text", "text": system_static, "cache_control": {"type": "ephemeral"}}, {"type": "text", "text": dynamic_context}],
                        messages=[{"role": "user", "content": user_message}],
                    )
                    text = "".join(block.text for block in response.content if block.type == "text")
                    usage = response.usage
                    output = int(usage.output_tokens)
                    cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
                    cache_write = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
                    real_input = int(usage.input_tokens) + cache_read + cache_write
                    # Contabilidade honesta: substitui a estimativa chars/4 pelo
                    # uso real da API antes de reservar a saída.
                    budget.reconcile(agent["agent_key"], estimated, real_input)
                    budget.reserve(agent["agent_key"], output)
                    budget.cache_read_tokens += cache_read
                    budget.cache_write_tokens += cache_write
                    return text, {
                        "input_tokens": real_input,
                        "output_tokens": output,
                        "cache_read_tokens": cache_read,
                        "cache_write_tokens": cache_write,
                    }
                except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError) as exc:
                    last_error = exc
                    await asyncio.sleep(0.25 * (2**attempt))
                    continue
                except anthropic.APIError:
                    break
        if last_error:
            return None, {"input_tokens": 0, "output_tokens": 0}
        return None, {"input_tokens": 0, "output_tokens": 0}
