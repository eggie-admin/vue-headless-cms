from __future__ import annotations

from dataclasses import dataclass

from app.models import AgentDecision, AgentRisk, ToolName


@dataclass(frozen=True)
class ToolPolicy:
    risk: AgentRisk
    requires_confirmation: bool
    local_allowed: bool = True


TOOL_POLICY: dict[ToolName, ToolPolicy] = {
    "respond": ToolPolicy("low", False),
    "get_system_status": ToolPolicy("low", False),
    "get_job_status": ToolPolicy("low", False),
    "inspect_cache": ToolPolicy("low", False),
    "set_avatar_state": ToolPolicy("low", False),
    "play_cutscene": ToolPolicy("low", False),
    "start_job": ToolPolicy("medium", False),
    "pause_job": ToolPolicy("low", False),
    "resume_job": ToolPolicy("low", False),
    "finalize_video": ToolPolicy("medium", True),
    "cleanup_cache": ToolPolicy("high", True),
    "upload_final": ToolPolicy("high", True, local_allowed=False),
}


def apply_policy(decision: AgentDecision) -> AgentDecision:
    policy = TOOL_POLICY[decision.tool]
    lane = decision.lane
    if lane == "local" and not policy.local_allowed:
        lane = "cloud"
    return decision.model_copy(
        update={
            "lane": lane,
            "risk": policy.risk,
            "requires_confirmation": policy.requires_confirmation,
        }
    )
