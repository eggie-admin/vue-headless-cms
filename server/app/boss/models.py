from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ProviderName = Literal["openai", "ollama", "gemini"]
FeedVerdict = Literal["ignore", "watch", "action"]


class FeedItem(BaseModel):
    item_id: str = Field(pattern=r"^[a-f0-9]{24}$")
    source_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_.-]+$")
    title: str = Field(default="", max_length=500)
    link: str = Field(default="", max_length=2000)
    summary: str = Field(default="", max_length=8000)
    published: str = Field(default="", max_length=120)
    external_id: str = Field(default="", max_length=2000)


class FeedAssessment(BaseModel):
    verdict: FeedVerdict
    summary: str = Field(min_length=1, max_length=1200)
    impact: str = Field(default="", max_length=1600)
    recommended_actions: list[str] = Field(default_factory=list, max_length=8)


class ProviderAssessmentResult(BaseModel):
    provider: ProviderName
    ok: bool
    assessment: FeedAssessment | None = None
    error: str | None = Field(default=None, max_length=500)


class FeedPollResult(BaseModel):
    source_id: str
    fetched: int
    new_items: list[FeedItem]
    executed: bool
    provider_results: dict[str, list[ProviderAssessmentResult]] = Field(default_factory=dict)
