import asyncio
import json
import logging
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .budget import BudgetExceeded
from .config import Settings, get_settings
from .database import DataStore, get_store, set_store, utcnow
from .llm import LLMGateway
from .metrics import metrics
from .models import AgentUpdate, ChatRequest, ChatResponse, TokenRequest
from .orchestration import OrchestrationService
from .rate_limit import SlidingWindowLimiter
from .security import current_customer, issue_token, request_identity_key, require_admin


settings = get_settings()
limiter = SlidingWindowLimiter(settings.rate_limit_requests, settings.rate_limit_window_seconds)
logger = logging.getLogger("multi-agent-poc")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def log(event: str, **fields) -> None:
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, default=str) if settings.log_json else f"{event} {fields}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = DataStore(settings)
    await store.connect()
    set_store(store)
    # DEMO_MODE nasce pronto; em Atlas o seed explícito também cria Search indexes.
    if store.memory:
        backend_dir = Path(__file__).resolve().parents[1]
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        from seed import seed

        await seed(store, create_indexes=False)
    app.state.orchestrator = OrchestrationService(store, LLMGateway(settings), settings.global_turn_token_budget)
    log("startup", storage="memory" if store.memory else "mongodb_atlas")
    yield
    await store.close()


app = FastAPI(title="Multi-Agent PoV", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Key", "X-Request-Id"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log("request_error", request_id=request_id, path=request.url.path)
        raise
    response.headers["X-Request-Id"] = request_id
    log("request", request_id=request_id, path=request.url.path, status=response.status_code, duration_ms=round((perf_counter() - started) * 1000, 2))
    return response


@app.exception_handler(BudgetExceeded)
async def budget_handler(_: Request, exc: BudgetExceeded):
    return JSONResponse(status_code=429, content={"detail": f"Turno encerrado com resposta parcial: {exc}"})


@app.post("/api/auth/token")
async def create_token(payload: TokenRequest, store: DataStore = Depends(get_store)):
    customer = await store.find_one("customers", {"customer_key": payload.customer_key})
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "identidade demo não encontrada")
    return {"access_token": issue_token(customer["customer_key"], settings), "token_type": "bearer", "customer": {key: customer[key] for key in ("customer_key", "name", "area", "plan")}}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: Request, payload: ChatRequest, customer: Annotated[dict, Depends(current_customer)]):
    if not limiter.allow(request_identity_key(request, customer["customer_key"])):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "limite de requisições excedido")
    async with metrics.track_route("chat"):
        try:
            return await asyncio.wait_for(
                request.app.state.orchestrator.run_turn(payload.message, customer, payload.conversation_id),
                timeout=settings.turn_deadline_seconds,
            )
        except TimeoutError as exc:
            await metrics.increment("turns.deadline_exceeded")
            raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, "deadline global do turno excedido") from exc


@app.get("/api/agents")
async def agents(_: Annotated[dict, Depends(current_customer)], store: DataStore = Depends(get_store)):
    items = await store.find_many("agent_registry", {}, brain=True, limit=20)
    return [{key: value for key, value in item.items() if key != "_id"} for item in items]


@app.get("/api/conversations/latest")
async def latest_conversation(customer: dict = Depends(current_customer), store: DataStore = Depends(get_store)):
    conversations = await store.find_many("agent_conversations", {"customer_key": customer["customer_key"]}, limit=1, sort=[("updated_at", -1)])
    if not conversations:
        return None
    conversation = {key: value for key, value in conversations[0].items() if key != "_id"}
    # sem isso, retomar a conversa mostra o texto certo mas a timeline/esteira ficam vazias — parece que o
    # multi-agent não rodou, quando na verdade só não foi recarregado o raio-x do último turno.
    traces = await store.find_many("agent_traces", {"conversation_id": conversation["conversation_id"]}, limit=1, sort=[("at", -1)])
    if traces:
        trace = traces[0]
        conversation["last_timeline"] = trace.get("timeline", [])
        conversation["last_usage"] = trace.get("usage", {})
    return conversation


@app.get("/api/handoffs")
async def handoffs(conversation_id: str = Query(min_length=4, max_length=80), customer: dict = Depends(current_customer), store: DataStore = Depends(get_store)):
    owner = await store.find_one("agent_conversations", {"conversation_id": conversation_id, "customer_key": customer["customer_key"]})
    if not owner:
        return []
    items = await store.find_many("agent_handoffs", {"conversation_id": conversation_id}, limit=100, sort=[("at", 1)])
    return [{key: value for key, value in item.items() if key != "_id"} for item in items]


@app.get("/api/memory/{customer_key}")
async def memory(customer_key: str, customer: dict = Depends(current_customer), store: DataStore = Depends(get_store)):
    if customer_key != customer["customer_key"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "memória pertence a outra identidade")
    items = await store.find_many("customer_memory", {"customer_key": customer_key, "active": True}, limit=50)
    return [{key: value for key, value in item.items() if key != "_id"} for item in items]


@app.get("/api/guardrails/{view}")
async def guardrails(view: str, _: dict = Depends(current_customer), store: DataStore = Depends(get_store)):
    mapping = {"events": "guardrail_events", "candidates": "guardrail_candidates", "denylist": "guardrail_denylist"}
    collection = mapping.get(view)
    if not collection:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "visão de guardrail desconhecida")
    items = await store.find_many(collection, {}, limit=100, sort=[("at" if view == "events" else "created_at", -1)])
    return [{key: value for key, value in item.items() if key != "_id"} for item in items]


@app.get("/api/events/stream")
async def events_stream(request: Request, customer: Annotated[dict, Depends(current_customer)], store: DataStore = Depends(get_store)):
    """Feed ao vivo de coordenação: Change Stream do Atlas em agent_handoffs, via SSE."""

    async def generator():
        async for event in store.watch_handoffs(customer["customer_key"]):
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/metrics")
async def get_metrics(_: dict = Depends(current_customer)):
    return metrics.snapshot()


@app.get("/api/health")
async def health(store: DataStore = Depends(get_store)):
    try:
        await store.ping()
        agents_count, handoffs_count, traces_count = await asyncio.gather(
            store.count("agent_registry", {"active": True}, brain=True), store.count("agent_handoffs"), store.count("agent_traces")
        )
        return {"status": "ok", "storage": "memory-demo" if store.memory else "mongodb-atlas", "mongodb": True, "anthropic_configured": bool(settings.anthropic_api_key), "counts": {"agents": agents_count, "handoffs": handoffs_count, "traces": traces_count}, "at": utcnow()}
    except Exception as exc:
        return JSONResponse(status_code=503, content={"status": "degraded", "mongodb": False, "detail": str(exc)})


@app.patch("/api/admin/agents/{agent_key}", dependencies=[Depends(require_admin)])
async def update_agent(agent_key: str, payload: AgentUpdate, store: DataStore = Depends(get_store)):
    update = {key: value for key, value in payload.model_dump().items() if value is not None}
    if not update:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "nenhuma alteração")
    changed = await store.update_one("agent_registry", {"agent_key": agent_key}, {"$set": update}, brain=True)
    if not changed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "agente não encontrado")
    await store.insert_one("admin_audit", {"action": "agent.update", "target": agent_key, "changes": update, "at": utcnow()})
    return {"ok": True, "agent_key": agent_key, "changes": update}


@app.post("/api/admin/guardrails/candidates/{candidate_id}/approve", dependencies=[Depends(require_admin)])
async def approve_candidate(candidate_id: str, store: DataStore = Depends(get_store)):
    candidate = await store.find_one("guardrail_candidates", {"_id": candidate_id})
    if not candidate:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "candidato não encontrado")
    phrase = candidate["text"]
    await store.replace_one("guardrail_denylist", {"phrase_norm": phrase.lower()}, {"phrase": phrase, "phrase_norm": phrase.lower(), "active": True}, upsert=True)
    await store.update_one("guardrail_candidates", {"_id": candidate_id}, {"$set": {"status": "approved"}})
    await store.insert_one("admin_audit", {"action": "guardrail.approve", "target": candidate_id, "at": utcnow()})
    return {"ok": True}


@app.get("/api/eval/runs", dependencies=[Depends(require_admin)])
async def eval_runs(store: DataStore = Depends(get_store)):
    """Histórico de qualidade (GoalSuccessRate por caso) — gravado por backend/eval.py a cada execução."""
    items = await store.find_many("eval_runs", {}, limit=30, sort=[("at", -1)])
    return [{key: value for key, value in item.items() if key != "_id"} for item in items]
