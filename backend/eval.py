"""Eval harness: roda o golden dataset (app/seed_data.py:EVAL_CASES) contra o servidor no ar,
mede GoalSuccessRate por caso e grava o resultado como documento em eval_runs — histórico de
qualidade fica no mesmo banco de dados, consultável como qualquer outro dado operacional.

Uso: python eval.py [URL]
"""

import asyncio
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import get_settings  # noqa: E402
from app.database import DataStore, utcnow  # noqa: E402
from app.seed_data import EVAL_CASES  # noqa: E402


BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8031"


def token(client: httpx.Client, customer_key: str) -> str:
    response = client.post("/api/auth/token", json={"customer_key": customer_key})
    response.raise_for_status()
    return response.json()["access_token"]


def run_case(client: httpx.Client, case: dict) -> dict:
    headers = {"Authorization": f"Bearer {token(client, case['customer_key'])}"}
    response = client.post("/api/chat", headers=headers, json={"message": case["message"]})
    response.raise_for_status()
    body = response.json()

    checks: list[tuple[str, bool]] = []
    if case.get("expect_blocked"):
        checks.append(("blocked", body["active_agent"] == "guardrail"))
    else:
        checks.append(("not_blocked", body["active_agent"] != "guardrail"))
    if case.get("expect_agent"):
        checks.append(("active_agent", body["active_agent"] == case["expect_agent"]))
    if case.get("expect_route_source"):
        checks.append(("route_source", body["route_source"] == case["expect_route_source"]))
    if case.get("expect_contains"):
        checks.append(("contains", case["expect_contains"] in body["response"]))

    passed = all(ok for _, ok in checks)
    return {
        "case_id": case["case_id"],
        "message": case["message"],
        "passed": passed,
        "checks": {name: ok for name, ok in checks},
        "active_agent": body["active_agent"],
        "route_source": body["route_source"],
        "response_preview": body["response"][:200],
    }


async def persist_run(results: list[dict], duration_s: float) -> None:
    store = DataStore(get_settings())
    await store.connect()
    try:
        passed = sum(1 for r in results if r["passed"])
        await store.insert_one(
            "eval_runs",
            {
                "at": utcnow(),
                "total": len(results),
                "passed": passed,
                "failed": len(results) - passed,
                "pass_rate": round(passed / max(1, len(results)), 4),
                "duration_s": round(duration_s, 2),
                "results": results,
            },
        )
    finally:
        await store.close()


def main() -> None:
    started = time.perf_counter()
    results = []
    with httpx.Client(base_url=BASE, timeout=60) as client:
        for case in EVAL_CASES:
            try:
                result = run_case(client, case)
            except Exception as exc:
                result = {"case_id": case["case_id"], "message": case["message"], "passed": False, "checks": {}, "error": str(exc)}
            results.append(result)
            mark = "✓" if result["passed"] else "✗"
            print(f"{mark} {result['case_id']}: {result.get('active_agent', '—')} / {result.get('route_source', '—')}")

    duration = time.perf_counter() - started
    passed = sum(1 for r in results if r["passed"])
    print(f"\n{passed}/{len(results)} casos passaram ({round(100 * passed / len(results))}%)")

    asyncio.run(persist_run(results, duration))
    print("[eval] resultado gravado em eval_runs")

    if passed < len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
