from __future__ import annotations

import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.cms.models import CmsDocument, CmsDocumentSummary, CmsRuntimeManifest, CmsUpsert

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = ROOT / "state" / "cms.sqlite3"
DEFAULT_TOKEN = ROOT / "state" / "cms-write-token.txt"


class CmsConflictError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_path() -> Path:
    return Path(os.getenv("CMS_STATE_DB", str(DEFAULT_DB))).expanduser()


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def ensure_database() -> None:
    with _connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS cms_documents (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cms_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                action TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        count = db.execute("SELECT COUNT(*) FROM cms_documents").fetchone()[0]
        if count == 0:
            seeds = {
                "ui-manifest": CmsUpsert(
                    kind="ui_manifest",
                    title="Cathedral UI Manifest",
                    payload={
                        "windows": [
                            {"id": "videoForge", "title": "Video Forge", "enabled": True},
                            {"id": "lumAgent", "title": "Lum Agent", "enabled": True},
                            {"id": "cutsceneDirector", "title": "Cutscene Director", "enabled": True},
                        ]
                    },
                ),
                "scene-manifest": CmsUpsert(
                    kind="scene_manifest",
                    title="Default Scene Manifest",
                    payload={"scene": "res://scenes/main.tscn", "avatar_state": "idle"},
                ),
                "content": CmsUpsert(
                    kind="content",
                    title="Cathedral Content",
                    payload={"headline": "Video Forge Cathedral", "status": "ready"},
                ),
            }
            for document_id, request in seeds.items():
                _upsert_with_connection(db, document_id, request)


def write_token() -> str:
    configured = os.getenv("VIDEO_FORGE_CMS_TOKEN")
    if configured:
        return configured
    path = Path(os.getenv("CMS_WRITE_TOKEN_FILE", str(DEFAULT_TOKEN))).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    token = secrets.token_urlsafe(32)
    path.write_text(token + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return token


def _row_to_document(row: sqlite3.Row) -> CmsDocument:
    return CmsDocument(
        id=row["id"],
        kind=row["kind"],
        title=row["title"],
        payload=json.loads(row["payload_json"]),
        revision=row["revision"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_documents() -> list[CmsDocumentSummary]:
    ensure_database()
    with _connect() as db:
        rows = db.execute(
            "SELECT id, kind, title, revision, updated_at FROM cms_documents ORDER BY kind, id"
        ).fetchall()
    return [CmsDocumentSummary(**dict(row)) for row in rows]


def get_document(document_id: str) -> CmsDocument | None:
    ensure_database()
    with _connect() as db:
        row = db.execute("SELECT * FROM cms_documents WHERE id = ?", (document_id,)).fetchone()
    return _row_to_document(row) if row else None


def _upsert_with_connection(db: sqlite3.Connection, document_id: str, request: CmsUpsert) -> CmsDocument:
    existing = db.execute("SELECT * FROM cms_documents WHERE id = ?", (document_id,)).fetchone()
    if existing and request.expected_revision is not None and existing["revision"] != request.expected_revision:
        raise CmsConflictError(
            f"revision mismatch for {document_id}: expected {request.expected_revision}, current {existing['revision']}"
        )
    now = _now()
    if existing:
        revision = int(existing["revision"]) + 1
        created_at = existing["created_at"]
        db.execute(
            "UPDATE cms_documents SET kind=?, title=?, payload_json=?, revision=?, updated_at=? WHERE id=?",
            (request.kind, request.title, json.dumps(request.payload, separators=(",", ":"), sort_keys=True), revision, now, document_id),
        )
        action = "updated"
    else:
        revision = 1
        created_at = now
        db.execute(
            "INSERT INTO cms_documents (id, kind, title, payload_json, revision, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (document_id, request.kind, request.title, json.dumps(request.payload, separators=(",", ":"), sort_keys=True), revision, created_at, now),
        )
        action = "created"
    db.execute(
        "INSERT INTO cms_events (document_id, action, revision, created_at) VALUES (?, ?, ?, ?)",
        (document_id, action, revision, now),
    )
    row = db.execute("SELECT * FROM cms_documents WHERE id = ?", (document_id,)).fetchone()
    return _row_to_document(row)


def upsert_document(document_id: str, request: CmsUpsert) -> CmsDocument:
    ensure_database()
    with _connect() as db:
        return _upsert_with_connection(db, document_id, request)


def delete_document(document_id: str, expected_revision: int | None = None) -> bool:
    ensure_database()
    with _connect() as db:
        existing = db.execute("SELECT revision FROM cms_documents WHERE id = ?", (document_id,)).fetchone()
        if not existing:
            return False
        if expected_revision is not None and existing["revision"] != expected_revision:
            raise CmsConflictError(
                f"revision mismatch for {document_id}: expected {expected_revision}, current {existing['revision']}"
            )
        revision = int(existing["revision"])
        db.execute("DELETE FROM cms_documents WHERE id = ?", (document_id,))
        db.execute(
            "INSERT INTO cms_events (document_id, action, revision, created_at) VALUES (?, 'deleted', ?, ?)",
            (document_id, revision, _now()),
        )
        return True


def runtime_manifest() -> CmsRuntimeManifest:
    ensure_database()
    with _connect() as db:
        rows = db.execute("SELECT * FROM cms_documents ORDER BY kind, id").fetchall()
        revision = db.execute("SELECT COALESCE(MAX(event_id), 0) FROM cms_events").fetchone()[0]
    return CmsRuntimeManifest(revision=int(revision), documents=[_row_to_document(row) for row in rows])
