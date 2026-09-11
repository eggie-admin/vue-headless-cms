from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import httpx

from app.boss.models import FeedItem

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class FeedSource:
    source_id: str
    url: str


def _clean_text(value: str | None, limit: int) -> str:
    text = html.unescape(value or "")
    text = _TAG_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text[:limit]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(node: ET.Element, names: set[str]) -> str:
    for child in list(node):
        if _local_name(child.tag) in names:
            return "".join(child.itertext()).strip()
    return ""


def _link_value(node: ET.Element) -> str:
    for child in list(node):
        if _local_name(child.tag) != "link":
            continue
        href = (child.attrib.get("href") or "").strip()
        if href:
            return href
        text = "".join(child.itertext()).strip()
        if text:
            return text
    return ""


def _item_id(source_id: str, external_id: str, link: str, title: str, published: str) -> str:
    seed = "\x1f".join((source_id, external_id, link, title, published))
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def parse_feed_document(source_id: str, document: bytes) -> list[FeedItem]:
    root = ET.fromstring(document)
    root_name = _local_name(root.tag)
    nodes: list[ET.Element]

    if root_name == "rss":
        channel = next((child for child in list(root) if _local_name(child.tag) == "channel"), root)
        nodes = [child for child in list(channel) if _local_name(child.tag) == "item"]
    elif root_name == "feed":
        nodes = [child for child in list(root) if _local_name(child.tag) == "entry"]
    else:
        raise ValueError(f"unsupported feed root: {root_name}")

    items: list[FeedItem] = []
    for node in nodes:
        title = _clean_text(_child_text(node, {"title"}), 500)
        link = _clean_text(_link_value(node), 2000)
        summary = _clean_text(_child_text(node, {"description", "summary", "content"}), 8000)
        published = _clean_text(_child_text(node, {"pubdate", "published", "updated"}), 120)
        external_id = _clean_text(_child_text(node, {"guid", "id"}), 2000)
        items.append(
            FeedItem(
                item_id=_item_id(source_id, external_id, link, title, published),
                source_id=source_id,
                title=title,
                link=link,
                summary=summary,
                published=published,
                external_id=external_id,
            )
        )
    return items


def load_feed_sources() -> dict[str, FeedSource]:
    raw = os.getenv("BOSS_FEEDS_JSON", "{}")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("BOSS_FEEDS_JSON must be an object mapping source id to HTTPS URL")
    if len(data) > 20:
        raise ValueError("too many feed sources")

    result: dict[str, FeedSource] = {}
    for source_id, url in data.items():
        if not isinstance(source_id, str) or not re.fullmatch(r"[a-z0-9_.-]{1,80}", source_id):
            raise ValueError("invalid feed source id")
        if not isinstance(url, str):
            raise ValueError(f"feed source {source_id} URL must be a string")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError(f"feed source {source_id} must use HTTPS")
        host = parsed.hostname.lower()
        if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
            raise ValueError(f"feed source {source_id} cannot target local addresses")
        result[source_id] = FeedSource(source_id=source_id, url=url)
    return result


async def fetch_feed(source_id: str) -> list[FeedItem]:
    sources = load_feed_sources()
    source = sources.get(source_id)
    if source is None:
        raise KeyError(f"unknown feed source: {source_id}")

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
        response = await client.get(
            source.url,
            headers={
                "accept": "application/atom+xml, application/rss+xml, application/xml, text/xml",
                "user-agent": "VideoForgeBossAI/1.0",
            },
        )
        response.raise_for_status()
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > 2_097_152:
            raise ValueError("feed document exceeds 2 MiB")
        body = response.content
    if len(body) > 2_097_152:
        raise ValueError("feed document exceeds 2 MiB")
    return parse_feed_document(source_id, body)[:10]


class FeedStore:
    def __init__(self, path: str | Path | None = None):
        configured = path or os.getenv("BOSS_STATE_DB") or str(
            Path(__file__).resolve().parents[3] / "state" / "boss.sqlite3"
        )
        self.path = str(configured)

    def _connect(self) -> sqlite3.Connection:
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS boss_feed_seen (
                item_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                first_seen_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        return connection

    def remember_new(self, items: list[FeedItem]) -> list[FeedItem]:
        new_items: list[FeedItem] = []
        with self._connect() as connection:
            for item in items:
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO boss_feed_seen(item_id, source_id) VALUES (?, ?)",
                    (item.item_id, item.source_id),
                )
                if cursor.rowcount == 1:
                    new_items.append(item)
        return new_items
