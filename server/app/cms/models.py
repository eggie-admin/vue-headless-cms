from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CmsKind = Literal[
    "ui_manifest",
    "scene_manifest",
    "content",
    "character_bible",
    "visual_bible",
    "asset_manifest",
    "cutscene",
]


class CmsUpsert(BaseModel):
    kind: CmsKind
    title: str = Field(min_length=1, max_length=160)
    payload: dict[str, Any]
    expected_revision: int | None = Field(default=None, ge=1)


class CmsDocument(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{0,79}$")
    kind: CmsKind
    title: str
    payload: dict[str, Any]
    revision: int = Field(ge=1)
    created_at: str
    updated_at: str


class CmsDocumentSummary(BaseModel):
    id: str
    kind: CmsKind
    title: str
    revision: int
    updated_at: str


class CmsRuntimeManifest(BaseModel):
    revision: int = Field(ge=0)
    documents: list[CmsDocument]
