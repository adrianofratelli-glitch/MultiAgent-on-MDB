import asyncio
from typing import Any

import anthropic

from .budget import TurnBudget, estimate_tokens
from .config import Settings


class LLMGateway:
    """Gateway Anthropic com retry transitório, fallback e prompt cache."""

    def __init__(self, settings: Settings):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None

    async def complete(
        self,
        *,
        agent: dict,
        user_message: str,
        dynamic_context: str,
        budget: TurnBudget,
    ) -> tuple[str | None, dict[str, int]]:
        if not self.client:
            return None, {"input_tokens": 0, "output_tokens": 0}
        estimated = estimate_tokens(agent["persona"] + user_message + dynamic_context)
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
                        system=[{"type": "text", "text": agent["persona"], "cache_control": {"type": "ephemeral"}}, {"type": "text", "text": dynamic_context}],
                        messages=[{"role": "user", "content": user_message}],
                    )
                    text = "".join(block.text for block in response.content if block.type == "text")
                    output = int(response.usage.output_tokens)
                    budget.reserve(agent["agent_key"], output)
                    return text, {"input_tokens": int(response.usage.input_tokens), "output_tokens": output}
                except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError) as exc:
                    last_error = exc
                    await asyncio.sleep(0.25 * (2**attempt))
                    continue
                except anthropic.APIError:
                    break
        if last_error:
            return None, {"input_tokens": 0, "output_tokens": 0}
        return None, {"input_tokens": 0, "output_tokens": 0}

