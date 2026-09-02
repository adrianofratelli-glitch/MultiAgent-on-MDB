import asyncio
from time import monotonic

import anthropic

from .budget import TurnBudget, estimate_tokens
from .config import Settings


# Circuit breaker leve, por processo, compartilhado entre TODAS as chamadas (mesmo turno e
# entre turnos) — não é estado por instância de LLMGateway porque o objetivo é justamente
# não pagar o retry completo (até 2 modelos x 3 tentativas) em cada uma das até 5 chamadas
# de um turno quando o provedor já está fora do ar. Abre depois de `FAILURE_THRESHOLD` falhas
# consecutivas e fica aberto por `OPEN_SECONDS`; depois disso, uma nova tentativa "meia-aberta"
# decide se fecha (sucesso) ou reabre a janela (falha).
FAILURE_THRESHOLD = 4
OPEN_SECONDS = 30.0


class _CircuitBreaker:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    async def allow(self) -> bool:
        """False quando o circuito está aberto e ainda dentro da janela de curto-circuito."""
        async with self._lock:
            if self._opened_at is None:
                return True
            if monotonic() - self._opened_at >= OPEN_SECONDS:
                # Janela expirou: deixa a próxima chamada testar o provedor (meio-aberto),
                # sem resetar o contador ainda — só um sucesso real fecha o circuito.
                self._opened_at = None
                return True
            return False

    async def record_success(self) -> None:
        async with self._lock:
            self._consecutive_failures = 0
            self._opened_at = None

    async def record_failure(self) -> None:
        async with self._lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= FAILURE_THRESHOLD:
                self._opened_at = monotonic()


# Único breaker do processo: intencionalmente um módulo-level singleton, não um atributo de
# LLMGateway — cada agente/turno cria contexto novo, mas o estado "o provedor está fora do
# ar" é uma verdade do processo inteiro, não de uma chamada isolada.
_circuit = _CircuitBreaker()


class LLMGateway:
    """Gateway Anthropic com retry transitório, fallback, prompt cache e circuit breaker."""

    def __init__(self, settings: Settings):
        self.client = anthropic.AsyncAnthropic(
            api_key="dummy",  # Grove/Azure APIM auth vai no header api-key, não x-api-key
            base_url=settings.anthropic_base_url or None,
            default_headers={"api-key": settings.anthropic_api_key},
            timeout=min(float(settings.turn_deadline_seconds), 60.0),
            max_retries=0,  # retries/fallback are explicit below and share the turn budget
        ) if settings.anthropic_api_key else None

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
        if not await _circuit.allow():
            # Curto-circuito: o provedor já falhou seguido o suficiente recentemente — reaproveita
            # o mesmo caminho de fallback de template usado quando não há client, em vez de pagar
            # até 2 modelos x 3 tentativas fadadas a estourar o turn_deadline_seconds.
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
                        max_tokens=min(agent.get("max_output_tokens") or agent["max_turn_tokens"], budget.global_limit - budget.total_used),
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
                    await _circuit.record_success()
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
        await _circuit.record_failure()
        if last_error:
            return None, {"input_tokens": 0, "output_tokens": 0}
        return None, {"input_tokens": 0, "output_tokens": 0}
