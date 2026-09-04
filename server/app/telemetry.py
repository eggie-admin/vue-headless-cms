from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger("video_forge.telemetry")

ALLOWED_EVENTS = {
    "cathedral_boot",
    "control_plane_health",
    "agent_routed",
    "agent_decision_rejected",
    "render_started",
    "render_completed",
    "render_failed",
    "cache_state_changed",
    "cutscene_started",
    "cutscene_completed",
    "feed_polled",
    "feed_item_new",
    "boss_provider_assessed",
    "boss_provider_failed",
}

BLOCKED_PROPERTY_FRAGMENTS = {
    "prompt",
    "secret",
    "token",
    "password",
    "path",
    "filename",
    "media",
    "email",
    "name",
    "title",
    "url",
    "link",
    "summary",
}


def sanitize_properties(properties: dict[str, Any]) -> dict[str, str | int | float | bool]:
    safe: dict[str, str | int | float | bool] = {}
    for key, value in properties.items():
        normalized = key.lower()
        if any(fragment in normalized for fragment in BLOCKED_PROPERTY_FRAGMENTS):
            continue
        if isinstance(value, (str, int, float, bool)):
            safe[key] = value
    return safe


async def emit_event(event: str, properties: dict[str, Any] | None = None) -> None:
    if event not in ALLOWED_EVENTS:
        raise ValueError(f"telemetry event is not allowlisted: {event}")

    safe = sanitize_properties(properties or {})
    logger.info("telemetry %s", json.dumps({"event": event, "properties": safe}, sort_keys=True))

    token = os.getenv("MIXPANEL_PROJECT_TOKEN")
    distinct_id = os.getenv("MIXPANEL_DISTINCT_ID")
    if not token or not distinct_id:
        return

    try:
        import mixpanel
    except ImportError:
        logger.warning("Mixpanel token configured but optional mixpanel package is not installed")
        return

    client = mixpanel.Mixpanel(token)
    await asyncio.to_thread(client.track, distinct_id, event, safe)
