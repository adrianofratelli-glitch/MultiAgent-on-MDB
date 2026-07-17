import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RouteDecision:
    intent: str
    target_agent: str | None
    source: str
    confidence: float


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in value if not unicodedata.combining(char))


def cheap_route(message: str, rules: Iterable[dict]) -> RouteDecision | None:
    """Resolve somente regras inequívocas; empates vão para o orquestrador."""
    text = normalize(message)
    scored: list[tuple[int, int, dict]] = []
    for rule in rules:
        seen_norms: set[str] = set()
        matches = 0
        for keyword in rule.get("keywords", []):
            keyword_norm = normalize(str(keyword))
            if keyword_norm in seen_norms:
                continue
            pattern = rf"(?<!\w){re.escape(keyword_norm)}(?!\w)"
            if re.search(pattern, text):
                matches += 1
                seen_norms.add(keyword_norm)
        if matches:
            scored.append((matches, int(rule.get("priority", 0)), rule))
    if not scored:
        return None
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best = scored[0]
    competing = [item for item in scored if item[:2] == best[:2]]
    targets = {item[2]["target_agent"] for item in competing}
    if len(targets) > 1:
        return None
    return RouteDecision(best[2]["intent"], best[2]["target_agent"], "rules", min(0.99, 0.7 + best[0] * 0.1))


FANOUT_ELIGIBLE = ("order_agent", "billing_agent")


def detect_fanout(message: str, rules: Iterable[dict]) -> list[str] | None:
    """Pattern 'Parallel Fan-Out': pedido composto ('status do pedido e quanto devo') dispara 2 agentes
    independentes ao mesmo tempo em vez de handoff sequencial — só entre agentes cujo trabalho é genuinamente
    independente (pedido/fatura). Se suporte/produto também tiverem sinal na mesma mensagem, ela tem uma
    dependência real de contexto (diagnóstico → recomendação → efetivação) e deve ir pela cadeia de handoff
    sequencial, não pelo fan-out — por isso aborta se qualquer agente fora do par elegível também bater."""
    text = normalize(message)
    hits: set[str] = set()
    for rule in rules:
        target = rule.get("target_agent")
        for keyword in rule.get("keywords", []):
            pattern = rf"(?<!\w){re.escape(normalize(str(keyword)))}(?!\w)"
            if re.search(pattern, text):
                hits.add(target)
                break
    if hits - set(FANOUT_ELIGIBLE):
        return None
    return sorted(hits) if len(hits) >= 2 else None


CATEGORY_KEYWORDS = {
    "fone": "Áudio", "caixa": "Áudio", "som": "Áudio",
    "teclado": "Periféricos", "mouse": "Periféricos",
    "monitor": "Monitores", "tela": "Monitores",
    "webcam": "Vídeo", "camera": "Vídeo",
    "smartwatch": "Vestíveis", "relogio": "Vestíveis",
    "carregador": "Energia",
    "hub": "Conectividade",
    "ssd": "Armazenamento", "armazenamento": "Armazenamento",
    "mochila": "Acessórios",
}


def deterministic_orchestrator(message: str) -> RouteDecision:
    text = normalize(message)
    if any(word in text for word in ("defeito", "quebrado", "nao funciona", "suporte", "nao conecta", "nao liga", "como resolvo")):
        return RouteDecision("suporte_tecnico", "support_agent", "orchestrator", 0.82)
    if any(word in text for word in ("produto", "parecido", "parecida", "recomenda", "mais barato", "mais barata")) or any(
        keyword in text for keyword in CATEGORY_KEYWORDS
    ):
        return RouteDecision("recomendacao", "product_agent", "orchestrator", 0.78)
    if any(word in text for word in ("fatura", "cobranca", "boleto")):
        return RouteDecision("cobranca", "billing_agent", "orchestrator", 0.82)
    return RouteDecision("pedido", "order_agent", "fallback", 0.55)

