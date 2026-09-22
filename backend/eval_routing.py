"""Eval de roteamento multiagente: acurácia de rota, taxa de resolução e handoffs por turno.

Formato do dataset e do relatório: `eval/FORMAT.md` (feito para a PoV singleagent reaproveitar
e permitir comparação direta — lá o roteamento é trivial, mas resolução e custo comparam).

    cd backend && ../.venv/bin/python eval_routing.py                    # DEMO_MODE, sem rede
    cd backend && ../.venv/bin/python eval_routing.py --live             # Atlas + LLM reais
    cd backend && ../.venv/bin/python eval_routing.py --json out.json --compare antes.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from statistics import mean
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import Settings, get_settings  # noqa: E402
from app.database import DataStore  # noqa: E402
from app.llm import LLMGateway  # noqa: E402
from app.orchestration import OrchestrationService  # noqa: E402
from seed import seed  # noqa: E402

DATASET = Path(__file__).resolve().parents[1] / "eval" / "routing_dataset.json"


async def _customers(store: DataStore) -> dict:
    rows = await store.find_many("customers", {}, limit=50)
    return {row["customer_key"]: row for row in rows}


def _routed_agent(response) -> str:
    """Agente de ENTRADA do turno — roteamento é a primeira decisão, não o fim da cadeia.

    Comparar com `active_agent` mediria a cadeia inteira: "trocar o produto com defeito por um
    parecido" entra no support_agent (diagnóstico) e termina no order_agent (efetivação); as
    duas coisas estão certas, mas só a primeira é roteamento.
    """
    agents = [event.agent for event in response.timeline if event.category == "agent" and event.agent]
    if response.route_source == "fanout":
        return "+".join(sorted(dict.fromkeys(agents)))
    return agents[0] if agents else response.active_agent


def _expected(case: dict) -> str:
    """Fan-out não tem ordem: o esperado é o CONJUNTO de agentes disparados em paralelo."""
    expected = case["expected_agent"]
    return "+".join(sorted(expected.split("+"))) if "+" in expected else expected


def _resolved(case: dict, response) -> bool:
    """Resolvido = o turno entregou o desfecho esperado, sem degradar e sem cair no genérico."""
    if response.degraded or not response.response.strip():
        return False
    if case.get("expect_blocked"):
        return response.active_agent == "guardrail"
    out_of_scope = any(event.result.get("out_of_scope") for event in response.timeline
                       if event.category == "guardrail")
    if case.get("expect_out_of_scope"):
        return bool(out_of_scope)
    return not out_of_scope and _routed_agent(response) == _expected(case)


async def run(live: bool) -> dict:
    settings = get_settings() if live else Settings(demo_mode=True, mongodb_uri="")
    store = DataStore(settings)
    await store.connect()
    if store.memory:
        await seed(store, create_indexes=False)
    service = OrchestrationService(store, LLMGateway(settings), settings.global_turn_token_budget)
    registry = await _customers(store)
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))

    rows = []
    for case in dataset["cases"]:
        customer = registry[case["customer"]]
        started = perf_counter()
        response = await service.run_turn(case["message"], customer, None)
        handoffs = [event for event in response.timeline
                    if event.category == "handoff" and (event.result or {}).get("to_agent")]
        chain = [event.agent for event in response.timeline if event.category == "agent" and event.agent]
        rows.append({
            "id": case["id"],
            "customer": case["customer"],
            "expected_agent": _expected(case),
            "actual_agent": _routed_agent(response),
            "final_agent": response.active_agent,
            "route_ok": _routed_agent(response) == _expected(case),
            "requires_llm": bool(case.get("requires_llm")),
            "route_source": response.route_source,
            "resolved": _resolved(case, response),
            "handoffs": len(handoffs),
            "min_handoffs_ok": len(handoffs) >= case.get("min_handoffs", 0),
            "chain": list(dict.fromkeys(chain)),
            "tokens": response.usage.get("total", 0),
            "degraded": response.degraded,
            "latency_ms": round((perf_counter() - started) * 1000, 1),
        })

    await store.close()
    # Casos marcados `requires_llm` não têm veredito honesto em DEMO_MODE (sem classificador
    # nem orquestrador LLM): entram na contagem, mas fora da acurácia do modo offline.
    scored = [row for row in rows if live or not row["requires_llm"]]
    summary = {
        "mode": "live" if live else "demo",
        "cases": len(rows),
        "scored_cases": len(scored),
        "skipped_requires_llm": len(rows) - len(scored),
        "routing_accuracy": round(mean(row["route_ok"] for row in scored), 4),
        "resolution_rate": round(mean(row["resolved"] for row in scored), 4),
        "avg_handoffs": round(mean(row["handoffs"] for row in rows), 3),
        "min_handoffs_respected": round(mean(row["min_handoffs_ok"] for row in rows), 4),
        "avg_tokens": round(mean(row["tokens"] for row in rows), 1),
        "degraded_turns": sum(row["degraded"] for row in rows),
        "synthetic": dataset["synthetic"],
        "limitation": dataset["limitation"],
    }
    return {"summary": summary, "rows": rows}


def report(result: dict, compare: dict | None) -> None:
    summary = result["summary"]
    print(f"\nmodo={summary['mode']}  casos={summary['cases']} (avaliados {summary['scored_cases']}, "
          f"{summary['skipped_requires_llm']} exigem LLM)  dataset sintético: {summary['synthetic']}")
    print(f"  acurácia de roteamento .... {summary['routing_accuracy']:.1%}")
    print(f"  taxa de resolução ......... {summary['resolution_rate']:.1%}")
    print(f"  handoffs por turno (média)  {summary['avg_handoffs']}")
    print(f"  tokens por turno (média) .. {summary['avg_tokens']}")
    print(f"  turnos degradados ......... {summary['degraded_turns']}")
    misses = [row for row in result["rows"]
              if (not row["route_ok"] or not row["resolved"])
              and (summary["mode"] == "live" or not row["requires_llm"])]
    if misses:
        print("\n  casos fora do esperado:")
        for row in misses:
            print(f"   - {row['id']} ({row['customer']}): esperado {row['expected_agent']}, "
                  f"obtido {row['actual_agent']} [{row['route_source']}] resolvido={row['resolved']}")
    if compare:
        before = compare["summary"]
        print("\n  comparação com o arquivo anterior:")
        for key in ("routing_accuracy", "resolution_rate", "avg_handoffs", "avg_tokens"):
            delta = summary[key] - before[key]
            print(f"   {key}: {before[key]} -> {summary[key]} ({delta:+.4f})")
    print(f"\n  limitação declarada: {summary['limitation']}")


async def main() -> int:
    parser = argparse.ArgumentParser(description="eval de roteamento/resolução multiagente")
    parser.add_argument("--live", action="store_true", help="usa Atlas e LLM reais (custa tokens)")
    parser.add_argument("--json", default="", help="grava o resultado completo")
    parser.add_argument("--compare", default="", help="compara com um resultado anterior")
    args = parser.parse_args()

    result = await run(args.live)
    compare = json.loads(Path(args.compare).read_text(encoding="utf-8")) if args.compare else None
    report(result, compare)
    if args.json:
        Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  resultado completo em {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
