"""Executa os candidatos de warmup e confirma quais entraram no cache semântico.

Cada chamada consome tokens reais do Claude. Apenas respostas aprovadas pela política stable_v1 ficam
disponíveis entre conversas; o relatório final explicita candidatos não elegíveis em vez de prometer HIT.

Uso: python warmup.py [URL]
"""

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.seed_data import DEMO_SCENARIOS  # noqa: E402
from app.router import normalize  # noqa: E402


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
    ready = 0
    skipped = 0
    with httpx.Client(base_url=BASE, timeout=120) as client:
        for customer_key, prompts in WARM_PROMPTS.items():
            headers = {"Authorization": f"Bearer {token(client, customer_key)}"}
            for message in prompts:
                response = client.post("/api/chat", headers=headers, json={"message": message})
                response.raise_for_status()
                body = response.json()
                done += 1
                cache_response = client.get("/api/inspector/cache", headers=headers)
                cache_response.raise_for_status()
                cache_items = cache_response.json().get("items", [])
                stored = any(item.get("question_norm") == normalize(message) for item in cache_items)
                if body["cache_hit"] or stored:
                    ready += 1
                    mark = "(já em cache)" if body["cache_hit"] else "(aquecido agora · stable_v1)"
                else:
                    skipped += 1
                    mark = "(executado · não elegível para cache)"
                print(f"[{done}/{total}] {customer_key}: {mark} — {message[:60]}...")
    print(f"\nPronto. {ready} candidato(s) disponível(is) no cache; {skipped} mantido(s) fora pela política stable_v1.")


if __name__ == "__main__":
    main()
