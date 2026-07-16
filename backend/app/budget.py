from dataclasses import dataclass, field


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class TurnBudget:
    global_limit: int
    per_agent_limits: dict[str, int]
    used_by_agent: dict[str, int] = field(default_factory=dict)

    @property
    def total_used(self) -> int:
        return sum(self.used_by_agent.values())

    def reserve(self, agent: str, tokens: int) -> None:
        agent_used = self.used_by_agent.get(agent, 0)
        if agent_used + tokens > self.per_agent_limits.get(agent, self.global_limit):
            raise BudgetExceeded(f"budget do agente {agent} excedido")
        if self.total_used + tokens > self.global_limit:
            raise BudgetExceeded("budget global do turno excedido")
        self.used_by_agent[agent] = agent_used + tokens


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)

