from __future__ import annotations

import asyncio
from contextlib import suppress

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.agents.router import Target, route_agent

app = FastAPI(title="Video Forge Control", version="0.1.0")


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


@app.get("/api/health")
async def health() -> dict[str, object]:
    return {"ok": True, **runtime}


@app.post("/api/avatar/state")
async def set_avatar_state(request: AvatarStateRequest) -> dict[str, object]:
    runtime["avatar_state"] = request.state
    return {"ok": True, **runtime}


@app.post("/api/agent/chat")
async def agent_chat(request: AgentRequest) -> dict[str, str]:
    provider, output = await route_agent(request.message, request.target)
    return {"provider": provider, "output": output}


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
