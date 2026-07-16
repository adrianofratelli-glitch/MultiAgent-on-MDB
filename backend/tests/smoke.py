"""Smoke test contra a API no ar. Uso: python tests/smoke.py [URL]."""

import sys

import httpx


BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"✓ {message}")


def token(client: httpx.Client, customer: str) -> str:
    response = client.post("/api/auth/token", json={"customer_key": customer})
    response.raise_for_status()
    return response.json()["access_token"]


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=130) as client:
        health = client.get("/api/health")
        check(health.status_code == 200 and health.json()["status"] == "ok", "health ok")

        ana = token(client, "ana")
        headers = {"Authorization": f"Bearer {ana}"}
        simple = client.post("/api/chat", headers=headers, json={"message": "onde está meu pedido PED-1001?"})
        simple.raise_for_status()
        body = simple.json()
        check(body["active_agent"] == "order_agent", "pedido roteado sem LLM")
        check("PED-1001" in body["response"] and "enviado" in body["response"], "pedido usa dado real do seed")

        handoff = client.post("/api/chat", headers=headers, json={"message": "meu fone chegou com defeito, quero um parecido mais barato"})
        handoff.raise_for_status()
        chain = handoff.json()
        check(chain["active_agent"] == "product_agent", "handoff suporte → produtos")
        audit = client.get("/api/handoffs", headers=headers, params={"conversation_id": chain["conversation_id"]})
        check(len(audit.json()) == 1 and audit.json()[0]["to_agent"] == "product_agent", "handoff persistido")

        bruno = token(client, "bruno")
        foreign = client.post("/api/chat", headers={"Authorization": f"Bearer {bruno}"}, json={"message": "onde está meu pedido PED-1001?"})
        foreign.raise_for_status()
        check("Não encontrei" in foreign.json()["response"], "isolamento entre clientes")

        repeated = client.post("/api/chat", headers=headers, json={"message": "onde está meu pedido PED-1001?"})
        repeated.raise_for_status()
        check(repeated.json()["cache_hit"] is True, "cache por agente e área")

        metrics = client.get("/api/metrics", headers=headers)
        check(metrics.status_code == 200 and "counters" in metrics.json(), "métricas disponíveis")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"✗ smoke falhou: {exc}", file=sys.stderr)
        raise SystemExit(1)

