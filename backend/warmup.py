"""Pré-aquece o cache semântico com as perguntas do roteiro de demo, ANTES da reunião com o cliente.

Isso é aquecimento de verdade: cada chamada aqui consome tokens reais do Claude, uma vez. Depois, quando
o cliente clicar no mesmo atalho ao vivo, a resposta vem do semantic_cache (cache_hit: true, visível na UI
sem nenhum disfarce) — sem inventar consumo de LLM que não aconteceu. Guardrail nunca é cacheado (o turno
é interrompido antes do cache), então perguntas de guardrail não entram aqui — não têm o que aquecer.

Uso: python warmup.py [URL]
"""

import sys

import httpx


BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8031"

# Espelha os atalhos não-guardrail de frontend/src/App.jsx:DEMOS_BY_IDENTITY — mesma frase exata, senão
# o cache não bate (chave é agent+area+customer_key+question_norm da mensagem).
WARM_PROMPTS = {
    "ana": [
        "meu pedido PED-1001 chegou com defeito, quero um parecido mais barato, e quero trocar — isso mexe na minha fatura?",
        "onde está meu pedido PED-1001 e quanto ainda devo na minha fatura?",
        "o pedido PED-1002 ainda está no prazo de garantia? se não estiver, quero um teclado parecido mais barato",
        "quero resgatar meus pontos de fidelidade por um produto",
    ],
    "bruno": [
        "meu monitor do pedido PED-2001 chegou com defeito, quero um parecido mais barato, e quero trocar — isso mexe na minha fatura?",
        "quero trocar o pedido PED-2001 e saber sobre a entrega dele",
        "meu pedido PED-2001 está na garantia? mesmo assim quero um monitor parecido mais barato",
        "quero resgatar meus pontos de fidelidade por um produto",
    ],
    "carla": [
        "meu smartwatch do pedido PED-3001 chegou com defeito, quero um parecido mais barato, e quero trocar — isso mexe na minha fatura?",
        "onde está meu pedido PED-3001 e minha fatura já foi paga?",
    ],
    "diego": [
        "minha caixa de som do pedido PED-4001 chegou com defeito, quero uma parecida mais barata, e quero trocar — isso mexe na minha fatura?",
        "quero trocar o pedido PED-4001 e saber sobre a entrega dele",
    ],
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
