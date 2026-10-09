from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AgentLane = Literal["local", "cloud"]
AgentRisk = Literal["low", "medium", "high"]
ToolName = Literal[
    "respond",
    "get_system_status",
    "get_job_status",
    "inspect_cache",
    "set_avatar_state",
    "play_cutscene",
    "start_job",
    "pause_job",
    "resume_job",
    "finalize_video",
    "cleanup_cache",
    "upload_final",
]


class AgentDecision(BaseModel):
    intent: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9_.-]+$")
    lane: AgentLane = "local"
    tool: ToolName = "respond"
    arguments: dict[str, Any] = Field(default_factory=dict)
    risk: AgentRisk = "low"
    requires_confirmation: bool = False
    rationale: str = Field(default="", max_length=500)
