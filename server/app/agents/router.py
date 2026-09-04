from __future__ import annotations

import os
from typing import Literal

import httpx
from agents import Agent, Runner

from app.models import AgentDecision
from app.policy import apply_policy

Target = Literal["auto", "local", "openai"]

LUM_INSTRUCTIONS = """
You are Lum, the Video Forge control antenna. Return exactly one typed decision.
Do not execute tools, do not invent filesystem paths, and do not emit shell
commands. Choose lane=local for low-risk local UI/status/media-control intents.
Choose lane=cloud when the request needs complex reasoning, coding, remote work,
or multimodal analysis. Python policy is authoritative for risk and confirmation.
""".strip()


def _cloud_agent() -> Agent:
    return Agent(
        name="Lum",
        instructions=LUM_INSTRUCTIONS,
        model=os.getenv("OPENAI_AGENT_MODEL", "gpt-5.6-sol"),
        output_type=AgentDecision,
    )


async def ask_openai(message: str) -> AgentDecision:
    result = await Runner.run(_cloud_agent(), message)
    output = result.final_output
    decision = output if isinstance(output, AgentDecision) else AgentDecision.model_validate(output)
    return apply_policy(decision)


async def ask_ollama(message: str) -> AgentDecision:
    base_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    model = os.getenv("OLLAMA_MODEL")
    if not model:
        raise RuntimeError("Local Ollama model is not configured")

    payload = {
        "model": model,
        "stream": False,
        "system": LUM_INSTRUCTIONS,
        "messages": [{"role": "user", "content": message}],
        "format": AgentDecision.model_json_schema(),
        "options": {"temperature": 0},
    }
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(f"{base_url.rstrip('/')}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
    decision = AgentDecision.model_validate_json(data["message"]["content"])
    return apply_policy(decision)


async def route_agent(message: str, target: Target = "auto") -> tuple[str, AgentDecision]:
    if target == "local":
        return "local", await ask_ollama(message)
    if target == "openai":
        return "openai", await ask_openai(message)

    if os.getenv("OLLAMA_MODEL"):
        try:
            local = await ask_ollama(message)
            if local.lane == "local":
                return "local", local
        except Exception:
            pass

    return "openai", await ask_openai(message)
