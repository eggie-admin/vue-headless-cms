from __future__ import annotations

import asyncio
from contextlib import suppress
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.wsgi import WSGIMiddleware

from app.agents.router import Target, route_agent
from app.flask_compat import compat_app
from app.telemetry import emit_event

app = FastAPI(title="Video Forge Control", version="0.2.0")


class AgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    target: Target = "auto"


class AvatarStateRequest(BaseModel):
    state: str = Field(pattern=r"^[a-z0-9_-]{1,40}$")


runtime = {
    "cache_state": "offline",
    "avatar_state": "idle",
    "progress": 0.0,
}

app.mount("/compat", WSGIMiddleware(compat_app))

WEB_DIST = Path(__file__).resolve().parents[2] / "apps" / "forge-ui" / "dist"
if WEB_DIST.is_dir():
    app.mount("/ui", StaticFiles(directory=WEB_DIST, html=True), name="forge-ui")


@app.on_event("startup")
async def startup_event() -> None:
    await emit_event("cathedral_boot", {"surface": "python-control-plane", "version": "0.2.0"})


@app.get("/api/health")
async def health() -> dict[str, object]:
    return {"ok": True, **runtime}


@app.post("/api/avatar/state")
async def set_avatar_state(request: AvatarStateRequest) -> dict[str, object]:
    runtime["avatar_state"] = request.state
    return {"ok": True, **runtime}


@app.post("/api/agent/chat")
async def agent_chat(request: AgentRequest) -> dict[str, object]:
    provider, decision = await route_agent(request.message, request.target)
    await emit_event(
        "agent_routed",
        {
            "provider": provider,
            "lane": decision.lane,
            "tool": decision.tool,
            "risk": decision.risk,
            "requires_confirmation": decision.requires_confirmation,
        },
    )
    return {"provider": provider, "decision": decision.model_dump()}


@app.websocket("/ws/events")
async def events(socket: WebSocket) -> None:
    await socket.accept()
    try:
        while True:
            await socket.send_json(runtime)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass
    finally:
        with suppress(Exception):
            await socket.close()
