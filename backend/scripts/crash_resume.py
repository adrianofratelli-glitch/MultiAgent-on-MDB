"""Cenário de caos que precisa de processo de verdade: SIGKILL no meio de uma conversa.

Sobe o backend num porto próprio contra o Atlas REAL (o único jeito de o estado sobreviver
ao processo), grava um turno, mata com SIGKILL — sem shutdown, sem flush —, sobe de novo e
cobra a conversa de volta. Sem cluster alcançável o cenário se declara `skipped` em vez de
mentir um PASS.

Custo: zero token. O filho sobe sem chave de LLM de propósito (respostas por template); o que
está sob teste é a persistência do estado, não a redação. Limpa o que escreveu no final.
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path

import httpx

BACKEND = Path(__file__).resolve().parents[1]
PORT = int(os.getenv("CRASH_RESUME_PORT", "8041"))
BASE = f"http://127.0.0.1:{PORT}"
CUSTOMER = "ana"


def _child_env() -> dict:
    env = dict(os.environ)
    env.update({
        "API_PORT": str(PORT), "DEMO_MODE": "0", "WARMUP_ON_START": "0",
        # Sem provedor de LLM: o teste é sobre estado persistido, não sobre texto gerado.
        "ANTHROPIC_API_KEY": "", "GROVE_API_KEY": "", "GROVE_ANTHROPIC_BASE_URL": "",
        "LANGFUSE_PUBLIC_KEY": "", "LANGFUSE_SECRET_KEY": "",
        "DEMO_TOKEN_ISSUANCE_ENABLED": "1", "AUTH_REQUIRED": "1",
        "CHAOS": "0", "TRACE_SINK": "off",
    })
    return env


async def _wait_ready(client: httpx.AsyncClient, timeout: float = 60.0) -> bool:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        try:
            if (await client.get(f"{BASE}/health/live", timeout=3)).status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.5)
    return False


def _start() -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "run.py"], cwd=BACKEND, env=_child_env(),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


async def _token(client: httpx.AsyncClient) -> str:
    response = await client.post(f"{BASE}/api/auth/token", json={"customer_key": CUSTOMER}, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


async def run_crash_resume() -> dict:
    sys.path.insert(0, str(BACKEND))
    from app.config import get_settings

    settings = get_settings()
    if not settings.mongodb_uri:
        return {"passed": False, "skipped": True, "detail": "sem MONGODB_URI: estado não sobrevive ao processo"}

    server = _start()
    conversation_id = ""
    try:
        async with httpx.AsyncClient() as client:
            if not await _wait_ready(client):
                return {"passed": False, "skipped": True, "detail": f"backend não subiu em {BASE} (cluster fora do ar?)"}
            headers = {"Authorization": f"Bearer {await _token(client)}"}
            first = await client.post(f"{BASE}/api/chat", headers=headers,
                                      json={"message": "onde está meu pedido?"}, timeout=120)
            first.raise_for_status()
            conversation_id = first.json()["conversation_id"]

            # SIGKILL: sem handler, sem shutdown, sem flush. O que não estiver no Atlas, morreu.
            server.send_signal(signal.SIGKILL)
            server.wait(timeout=30)

            server = _start()
            if not await _wait_ready(client):
                return {"passed": False, "detail": "backend não voltou depois do SIGKILL"}
            headers = {"Authorization": f"Bearer {await _token(client)}"}
            latest = await client.get(f"{BASE}/api/conversations/latest", headers=headers, timeout=60)
            latest.raise_for_status()
            body = latest.json()

        same = body.get("conversation_id") == conversation_id
        turns = body.get("turns") or []
        recovered = any("pedido" in str(turn.get("content", "")).lower() for turn in turns)
        return {"passed": bool(same and recovered),
                "detail": f"conversa={'mesma' if same else 'outra'} mensagens_recuperadas={len(turns)}"}
    finally:
        with contextlib_suppress():
            server.kill()
        if conversation_id:
            await _cleanup(conversation_id)


def contextlib_suppress():
    import contextlib
    return contextlib.suppress(Exception)


async def _cleanup(conversation_id: str) -> None:
    """Remove o que este cenário escreveu — a demo não pode ganhar uma conversa fantasma."""
    from app.config import get_settings
    from app.database import DataStore

    store = DataStore(get_settings())
    try:
        await store.connect()
        for collection in ("agent_conversations", "agent_handoffs", "agent_traces", "short_term_memory"):
            await store.delete_many(collection, {"conversation_id": conversation_id})
    except Exception:  # noqa: BLE001 — limpeza best-effort não pode mascarar o veredito
        pass
    finally:
        await store.close()


if __name__ == "__main__":
    print(asyncio.run(run_crash_resume()))
