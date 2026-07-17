"""Pré-aquece o cache semântico com as perguntas do roteiro de demo, ANTES da reunião com o cliente.

Isso é aquecimento de verdade: cada chamada aqui consome tokens reais do Claude, uma vez. Depois, quando
o cliente clicar no mesmo atalho ao vivo, a resposta vem do semantic_cache (cache_hit: true, visível na UI
sem nenhum disfarce) — sem inventar consumo de LLM que não aconteceu. Guardrail nunca é cacheado (o turno
é interrompido antes do cache), então perguntas de guardrail não entram aqui — não têm o que aquecer.

Uso: python warmup.py [URL]
"""

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.seed_data import DEMO_SCENARIOS  # noqa: E402


BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8031"

# Só pré-aquece cenários read-only explicitamente marcados. Writes, guardrails e cadeias com retorno
# continuam frios para que a demo mostre a execução real e não esconda ações atrás de cache.
WARM_PROMPTS = {
    customer_key: [
        scenario["message"]
        for scenario in DEMO_SCENARIOS
        if scenario["customer_key"] == customer_key and scenario.get("warmup")
    ]
    for customer_key in {scenario["customer_key"] for scenario in DEMO_SCENARIOS}
}


def token(client: httpx.Client, customer_key: str) -> str:
    response = client.post("/api/auth/token", json={"customer_key": customer_key})
    response.raise_for_status()
    return response.json()["access_token"]


def main() -> None:
    total = sum(len(prompts) for prompts in WARM_PROMPTS.values())
    done = 0
    with httpx.Client(base_url=BASE, timeout=120) as client:
        for customer_key, prompts in WARM_PROMPTS.items():
            headers = {"Authorization": f"Bearer {token(client, customer_key)}"}
            for message in prompts:
                response = client.post("/api/chat", headers=headers, json={"message": message})
                response.raise_for_status()
                body = response.json()
                done += 1
                mark = "(já em cache)" if body["cache_hit"] else "(aquecido agora)"
                print(f"[{done}/{total}] {customer_key}: {mark} — {message[:60]}...")
    print(f"\nPronto. {total} atalhos de demo pré-aquecidos — o primeiro clique ao vivo do cliente vem do cache.")


if __name__ == "__main__":
    main()
