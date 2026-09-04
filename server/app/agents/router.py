from __future__ import annotations

import os
from typing import Literal

import httpx
from agents import Agent, Runner

Target = Literal["auto", "local", "openai"]

LUM_INSTRUCTIONS = """
You are Lum, the Video Forge control agent. Prefer typed, reversible actions.
Never invent filesystem paths, never issue arbitrary shell commands, and never
claim a render or upload completed without tool evidence. Local media state and
structured project state outrank conversational guesses.
""".strip()


def _cloud_agent() -> Agent:
    return Agent(
        name="Lum",
        instructions=LUM_INSTRUCTIONS,
        model=os.getenv("OPENAI_AGENT_MODEL", "gpt-5.6-sol"),
    )


async def ask_openai(message: str) -> str:
    result = await Runner.run(_cloud_agent(), message)
    return str(result.final_output)


async def ask_ollama(message: str) -> str:
    base_url = os.getenv("OLLAMA_URL")
    model = os.getenv("OLLAMA_MODEL")
    if not base_url or not model:
        raise RuntimeError("Local Ollama is not configured on this runtime")

    payload = {
        "model": model,
        "stream": False,
        "messages": [{"role": "user", "content": message}],
    }
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(f"{base_url.rstrip('/')}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
    return str(data["message"]["content"])


async def route_agent(message: str, target: Target = "auto") -> tuple[str, str]:
    if target == "local":
        return "local", await ask_ollama(message)
    if target == "openai":
        return "openai", await ask_openai(message)

    # Auto is deliberately conservative: use the local model only when the
    # runtime explicitly configured one. More sophisticated intent/risk routing
    # belongs behind a typed policy layer, not substring heuristics.
    if os.getenv("OLLAMA_URL") and os.getenv("OLLAMA_MODEL"):
        try:
            return "local", await ask_ollama(message)
        except Exception:
            pass
    return "openai", await ask_openai(message)
