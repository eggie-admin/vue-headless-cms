from __future__ import annotations

import asyncio
from contextlib import suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.wsgi import WSGIMiddleware

from app.agents.router import Target, route_agent
from app.boss.manifest import load_manifest, manifest_base64, manifest_sha256, verify_base64_copy
from app.boss.providers import auto_fanout_enabled, provider_readiness
from app.boss.service import poll_feed_source
from app.flask_compat import compat_app
from app.telemetry import emit_event

app = FastAPI(title="Video Forge Control", version="0.3.0")


class AgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    target: Target = "auto"


class AvatarStateRequest(BaseModel):
    state: str = Field(pattern=r"^[a-z0-9_-]{1,40}$")


class FeedPollRequest(BaseModel):
    execute: bool = False


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
    await emit_event("cathedral_boot", {"surface": "python-control-plane", "version": "0.3.0"})


@app.get("/api/health")
async def health() -> dict[str, object]:
    return {"ok": True, **runtime}


@app.get("/api/boss/manifest")
async def boss_manifest() -> dict[str, object]:
    return {
        "ok": True,
        "sha256": manifest_sha256(),
        "base64_roundtrip": verify_base64_copy(),
        "manifest": load_manifest(),
        "manifest_base64": manifest_base64(),
    }


@app.get("/api/boss/providers")
async def boss_providers() -> dict[str, object]:
    return {
        "ok": True,
        "configured": provider_readiness(),
        "auto_fanout_enabled": auto_fanout_enabled(),
    }


@app.post("/api/boss/feeds/{source_id}/poll")
async def boss_poll_feed(source_id: str, request: FeedPollRequest) -> dict[str, object]:
    try:
        result = await poll_feed_source(source_id, execute=request.execute)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await emit_event(
        "feed_polled",
        {
            "source_id": source_id,
            "fetched": result.fetched,
            "new_count": len(result.new_items),
            "executed": result.executed,
        },
    )
    for provider_results in result.provider_results.values():
        for provider_result in provider_results:
            await emit_event(
                "boss_provider_assessed" if provider_result.ok else "boss_provider_failed",
                {
                    "provider": provider_result.provider,
                    "ok": provider_result.ok,
                },
            )
    return {
        "ok": True,
        "auto_fanout_enabled": auto_fanout_enabled(),
        "result": result.model_dump(),
    }


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
