#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import time
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "manifests/vendor-docs.manifest.json"


class TextExtractor(HTMLParser):
    SKIP = {"script", "style", "svg", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in self.SKIP:
            self.skip_depth += 1
        elif not self.skip_depth and tag.lower() in {"p", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "code", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.SKIP and self.skip_depth:
            self.skip_depth -= 1
        elif not self.skip_depth and tag.lower() in {"p", "li", "pre", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        raw = unescape("".join(self.parts))
        raw = raw.replace("\r\n", "\n").replace("\r", "\n")
        raw = re.sub(r"[\t ]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_registry(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    policy = data["policy"]
    if not policy.get("https_only") or not policy.get("official_vendor_sources_only"):
        raise ValueError("vendor registry must be HTTPS-only and official-source-only")
    seen_ids: set[str] = set()
    url_count = 0
    for vendor in data["vendors"]:
        vendor_id = vendor["id"]
        if vendor_id in seen_ids:
            raise ValueError(f"duplicate vendor id: {vendor_id}")
        seen_ids.add(vendor_id)
        hosts = set(vendor["hosts"])
        for url in vendor["urls"]:
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.hostname not in hosts:
                raise ValueError(f"URL violates vendor host policy: {url}")
            if parsed.username or parsed.password:
                raise ValueError(f"userinfo forbidden in vendor URL: {url}")
            url_count += 1
    if url_count > int(policy["max_documents_per_run"]):
        raise ValueError("registry exceeds max_documents_per_run")
    return data


def normalize_document(raw: bytes, content_type: str) -> str:
    text = raw.decode("utf-8", errors="replace")
    if "html" in content_type.lower() or "<html" in text[:1000].lower():
        parser = TextExtractor()
        parser.feed(text)
        text = parser.text()
    else:
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    return text


def chunk_document(text: str, max_chars: int, overlap_chars: int) -> list[tuple[int, int, str]]:
    if not text:
        return []
    chunks: list[tuple[int, int, str]] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = text.rfind("\n", start + max_chars // 2, end)
            if boundary > start:
                end = boundary
        body = text[start:end].strip()
        if body:
            chunks.append((start, end, body))
        if end >= len(text):
            break
        start = max(start + 1, end - overlap_chars)
    return chunks


def fetch_one(url: str, hosts: set[str], policy: dict) -> tuple[str, bytes, str]:
    request = Request(url, headers={"User-Agent": policy["user_agent"], "Accept": "text/html,text/plain,application/json;q=0.9,*/*;q=0.1"})
    with urlopen(request, timeout=20) as response:
        final_url = response.geturl()
        parsed = urlparse(final_url)
        if parsed.scheme != "https" or parsed.hostname not in hosts:
            raise ValueError(f"redirect escaped allowlist: {final_url}")
        max_bytes = int(policy["max_document_bytes"])
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ValueError("document exceeds max_document_bytes")
        content_type = response.headers.get("Content-Type", "text/plain")
        return final_url, raw, content_type


def build_corpus(registry: dict, output_dir: Path, *, limit: int | None = None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    policy = registry["policy"]
    documents: list[dict] = []
    chunks: list[dict] = []
    failures: list[dict] = []
    requested = 0

    for vendor in registry["vendors"]:
        hosts = set(vendor["hosts"])
        for url in vendor["urls"]:
            if limit is not None and requested >= limit:
                break
            requested += 1
            try:
                final_url, raw, content_type = fetch_one(url, hosts, policy)
                text = normalize_document(raw, content_type)
                raw_sha = sha256(raw)
                text_sha = sha256(text.encode("utf-8"))
                chunk_ids: list[str] = []
                for start, end, body in chunk_document(text, int(policy["max_chunk_chars"]), int(policy["overlap_chars"])):
                    chunk_sha = sha256(body.encode("utf-8"))
                    chunk_id = sha256(f"{vendor['id']}:{url}:{start}:{end}:{chunk_sha}".encode("utf-8"))[:24]
                    chunk_ids.append(chunk_id)
                    chunks.append({
                        "chunk_id": chunk_id,
                        "vendor_id": vendor["id"],
                        "vendor": vendor["name"],
                        "url": url,
                        "final_url": final_url,
                        "start_char": start,
                        "end_char": end,
                        "document_sha256": text_sha,
                        "chunk_sha256": chunk_sha,
                        "text": body,
                        "trust": "untrusted_documentation_data"
                    })
                documents.append({
                    "vendor_id": vendor["id"],
                    "vendor": vendor["name"],
                    "url": url,
                    "final_url": final_url,
                    "content_type": content_type,
                    "bytes": len(raw),
                    "raw_sha256": raw_sha,
                    "text_sha256": text_sha,
                    "chunks": chunk_ids
                })
            except Exception as exc:
                failures.append({"vendor_id": vendor["id"], "url": url, "error": type(exc).__name__})
        if limit is not None and requested >= limit:
            break

    corpus_path = output_dir / registry["outputs"]["corpus"]
    with corpus_path.open("w", encoding="utf-8", newline="\n") as fh:
        for item in chunks:
            fh.write(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")

    manifest = {
        "schema_version": registry["schema_version"],
        "project": registry["project"],
        "generated_unix": int(time.time()),
        "policy": {
            "official_vendor_sources_only": True,
            "https_only": True,
            "documentation_is_untrusted_data": True,
            "execute_document_code": False,
            "redistribute": False
        },
        "counts": {"requested": requested, "documents": len(documents), "chunks": len(chunks), "failures": len(failures)},
        "corpus": {"path": corpus_path.name, "sha256": sha256(corpus_path.read_bytes())},
        "documents": documents
    }
    (output_dir / registry["outputs"]["manifest"]).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / registry["outputs"]["fetch_report"]).write_text(json.dumps({"failures": failures}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def smoke() -> None:
    registry = load_registry(DEFAULT_REGISTRY)
    assert len(registry["vendors"]) >= 20
    assert sum(len(v["urls"]) for v in registry["vendors"]) >= 40
    sample = "<html><body><h1>Vendor</h1><script>ignore_me()</script><p>Models propose. Python authorizes.</p></body></html>"
    text = normalize_document(sample.encode(), "text/html")
    assert "ignore_me" not in text and "Python authorizes" in text
    parts = chunk_document(text * 100, 500, 50)
    assert parts
    with tempfile.TemporaryDirectory(prefix="vendor-docs-smoke-") as tmp:
        Path(tmp, "ok.txt").write_text(text, encoding="utf-8")
    print(f"VENDOR_DOCS_SMOKE_GREEN vendors={len(registry['vendors'])} urls={sum(len(v['urls']) for v in registry['vendors'])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and chunk allowlisted official vendor documentation into a local untrusted research corpus.")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--output", default="state/vendor-docs")
    parser.add_argument("--fetch", action="store_true", help="Perform HTTPS fetches. Without this flag only validate the registry.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    if args.smoke:
        smoke()
        return

    registry = load_registry(Path(args.registry))
    if not args.fetch:
        print(f"VENDOR_DOCS_REGISTRY_GREEN vendors={len(registry['vendors'])} urls={sum(len(v['urls']) for v in registry['vendors'])}")
        return

    result = build_corpus(registry, Path(args.output), limit=args.limit)
    print("VENDOR_DOCS_INGEST_COMPLETE " + " ".join(f"{k}={v}" for k, v in result["counts"].items()))


if __name__ == "__main__":
    main()
