#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

SCHEMA_VERSION = "1.0.0"
PROJECT_NAME = "Samsung SM-X400"
MAX_FILE_BYTES_DEFAULT = 512 * 1024
MAX_CHUNK_LINES_DEFAULT = 120
MAX_CHUNK_CHARS_DEFAULT = 12_000
OVERLAP_LINES_DEFAULT = 12

TEXT_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".css", ".gd", ".go", ".gradle", ".h", ".hpp",
    ".html", ".ini", ".java", ".js", ".json", ".kt", ".kts", ".md",
    ".mjs", ".py", ".rs", ".sh", ".sql", ".toml", ".ts", ".tsx", ".txt",
    ".vue", ".xml", ".yaml", ".yml", ".cfg",
}
SPECIAL_TEXT_NAMES = {"Dockerfile", "Makefile", "AGENTS.md", "README.md"}
EXCLUDED_DIRS = {
    ".git", ".gradle", ".idea", ".venv", "__pycache__", "build", "dist", "logs",
    "node_modules", "private", "state", "tmp", "vendor",
}
SECRET_NAME_MARKERS = {
    "credential", "credentials", "passwd", "password", "secret", "secrets", "token",
}
SECRET_SUFFIXES = {
    ".der", ".jks", ".key", ".keystore", ".p12", ".pem", ".pfx", ".sqlite", ".sqlite3",
}


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    path: str
    language: str
    file_sha256: str
    chunk_sha256: str
    start_line: int
    end_line: int
    text: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def language_for(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".py": "python", ".gd": "gdscript", ".kt": "kotlin", ".kts": "kotlin",
        ".js": "javascript", ".mjs": "javascript", ".ts": "typescript", ".tsx": "typescript",
        ".vue": "vue", ".sh": "shell", ".json": "json", ".toml": "toml",
        ".yaml": "yaml", ".yml": "yaml", ".xml": "xml", ".html": "html",
        ".css": "css", ".sql": "sql", ".md": "markdown", ".java": "java",
        ".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".hpp": "cpp",
        ".go": "go", ".rs": "rust", ".gradle": "gradle", ".ini": "ini", ".cfg": "config",
    }.get(suffix, "text")


def is_secretish_name(path: Path) -> bool:
    name = path.name.lower()
    if name == ".env" or name.startswith(".env.") or name.endswith(".env"):
        return True
    if path.suffix.lower() in SECRET_SUFFIXES:
        return True
    stem_tokens = {token for token in name.replace("-", "_").replace(".", "_").split("_") if token}
    return bool(stem_tokens & SECRET_NAME_MARKERS)


def should_ingest(path: Path, root: Path, max_file_bytes: int) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    if path.is_symlink() or not path.is_file():
        return False
    if any(part in EXCLUDED_DIRS for part in rel.parts[:-1]):
        return False
    if is_secretish_name(path):
        return False
    if path.name not in SPECIAL_TEXT_NAMES and path.suffix.lower() not in TEXT_EXTENSIONS:
        return False
    try:
        return path.stat().st_size <= max_file_bytes
    except OSError:
        return False


def iter_source_files(root: Path, max_file_bytes: int) -> Iterable[Path]:
    for path in sorted(root.rglob("*"), key=lambda p: p.as_posix()):
        if should_ingest(path, root, max_file_bytes):
            yield path


def chunk_text(
    text: str,
    max_lines: int,
    max_chars: int,
    overlap_lines: int,
) -> list[tuple[int, int, str]]:
    lines = text.splitlines()
    if not lines:
        return []
    chunks: list[tuple[int, int, str]] = []
    start = 0
    while start < len(lines):
        end = min(start + max_lines, len(lines))
        while end > start + 1 and len("\n".join(lines[start:end])) > max_chars:
            end -= 1
        body = "\n".join(lines[start:end]).strip("\n")
        if body:
            chunks.append((start + 1, end, body))
        if end >= len(lines):
            break
        next_start = max(start + 1, end - overlap_lines)
        if next_start <= start:
            next_start = start + 1
        start = next_start
    return chunks


def build_ingest(
    root: Path,
    output_dir: Path,
    *,
    max_file_bytes: int = MAX_FILE_BYTES_DEFAULT,
    max_chunk_lines: int = MAX_CHUNK_LINES_DEFAULT,
    max_chunk_chars: int = MAX_CHUNK_CHARS_DEFAULT,
    overlap_lines: int = OVERLAP_LINES_DEFAULT,
) -> dict:
    root = root.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks: list[Chunk] = []
    files: list[dict] = []
    skipped_decode = 0

    for path in iter_source_files(root, max_file_bytes):
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            skipped_decode += 1
            continue
        rel = path.relative_to(root).as_posix()
        file_sha = sha256_bytes(raw)
        language = language_for(path)
        file_chunks = chunk_text(text, max_chunk_lines, max_chunk_chars, overlap_lines)
        chunk_ids: list[str] = []
        for start_line, end_line, body in file_chunks:
            body_bytes = body.encode("utf-8")
            chunk_sha = sha256_bytes(body_bytes)
            chunk_id = sha256_bytes(f"{rel}:{start_line}:{end_line}:{chunk_sha}".encode("utf-8"))[:24]
            chunk_ids.append(chunk_id)
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    path=rel,
                    language=language,
                    file_sha256=file_sha,
                    chunk_sha256=chunk_sha,
                    start_line=start_line,
                    end_line=end_line,
                    text=body,
                )
            )
        files.append(
            {
                "path": rel,
                "language": language,
                "bytes": len(raw),
                "sha256": file_sha,
                "chunks": chunk_ids,
            }
        )

    chunks_path = output_dir / "source-chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8", newline="\n") as fh:
        for chunk in chunks:
            fh.write(json.dumps(asdict(chunk), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            fh.write("\n")

    chunks_sha = sha256_bytes(chunks_path.read_bytes())
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "project": PROJECT_NAME,
        "root": ".",
        "policy": {
            "read_only": True,
            "execute_source": False,
            "follow_symlinks": False,
            "secret_files_excluded": True,
            "build_artifacts_excluded": True,
            "max_file_bytes": max_file_bytes,
            "max_chunk_lines": max_chunk_lines,
            "max_chunk_chars": max_chunk_chars,
            "overlap_lines": overlap_lines,
        },
        "counts": {
            "files": len(files),
            "chunks": len(chunks),
            "decode_skips": skipped_decode,
        },
        "corpus": {
            "path": "source-chunks.jsonl",
            "sha256": chunks_sha,
        },
        "files": files,
    }
    manifest_path = output_dir / "source-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def smoke() -> None:
    with tempfile.TemporaryDirectory(prefix="source-ingest-smoke-") as tmp:
        root = Path(tmp) / "repo"
        out1 = Path(tmp) / "out1"
        out2 = Path(tmp) / "out2"
        (root / "src").mkdir(parents=True)
        (root / "state").mkdir()
        (root / "node_modules").mkdir()
        (root / "src" / "main.py").write_text("def hello():\n    return 'green'\n", encoding="utf-8")
        (root / "src" / "ui.vue").write_text("<template><div>green</div></template>\n", encoding="utf-8")
        (root / ".env").write_text("OPENAI_API_KEY=do-not-ingest\n", encoding="utf-8")
        (root / "src" / "api-token.txt").write_text("do-not-ingest\n", encoding="utf-8")
        (root / "state" / "runtime.json").write_text("{\"secret\":true}\n", encoding="utf-8")
        (root / "node_modules" / "junk.js").write_text("junk\n", encoding="utf-8")
        m1 = build_ingest(root, out1, max_chunk_lines=2, overlap_lines=1)
        m2 = build_ingest(root, out2, max_chunk_lines=2, overlap_lines=1)
        paths = {item["path"] for item in m1["files"]}
        assert "src/main.py" in paths
        assert "src/ui.vue" in paths
        assert ".env" not in paths
        assert "src/api-token.txt" not in paths
        assert "state/runtime.json" not in paths
        assert "node_modules/junk.js" not in paths
        assert m1["corpus"]["sha256"] == m2["corpus"]["sha256"]
        assert (out1 / "source-manifest.json").read_text(encoding="utf-8") == (out2 / "source-manifest.json").read_text(encoding="utf-8")
        assert "do-not-ingest" not in (out1 / "source-chunks.jsonl").read_text(encoding="utf-8")
        print(f"SOURCE_INGEST_SMOKE_GREEN files={m1['counts']['files']} chunks={m1['counts']['chunks']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a deterministic, secret-aware source corpus for Samsung SM-X400 AI retrieval.")
    parser.add_argument("--root", default=".", help="Repository root to scan")
    parser.add_argument("--output", default="state/source-ingest", help="Output directory")
    parser.add_argument("--max-file-bytes", type=int, default=MAX_FILE_BYTES_DEFAULT)
    parser.add_argument("--max-chunk-lines", type=int, default=MAX_CHUNK_LINES_DEFAULT)
    parser.add_argument("--max-chunk-chars", type=int, default=MAX_CHUNK_CHARS_DEFAULT)
    parser.add_argument("--overlap-lines", type=int, default=OVERLAP_LINES_DEFAULT)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    if args.smoke:
        smoke()
        return

    manifest = build_ingest(
        Path(args.root),
        Path(args.output),
        max_file_bytes=args.max_file_bytes,
        max_chunk_lines=args.max_chunk_lines,
        max_chunk_chars=args.max_chunk_chars,
        overlap_lines=args.overlap_lines,
    )
    print(
        "SOURCE_INGEST_GREEN "
        f"files={manifest['counts']['files']} "
        f"chunks={manifest['counts']['chunks']} "
        f"sha256={manifest['corpus']['sha256']}"
    )


if __name__ == "__main__":
    main()
