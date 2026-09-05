#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "manifests" / "oss-vendors.lock.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
USES = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)", re.MULTILINE)
MUTABLE_VCS = re.compile(
    r"(?:git\+https://github\.com/|https://github\.com/[^\s'\"]+\.git@)"
    r"[^\s'\"]*@(main|master|develop|dev|head)\b",
    re.IGNORECASE,
)


def fail(message: str) -> None:
    print(f"VENDOR_SANITY_FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_lock() -> dict:
    try:
        data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"cannot read {LOCK_PATH}: {exc}")
    if data.get("policy", {}).get("default") != "deny":
        fail("vendor policy must be default-deny")
    return data


def validate_hex(label: str, value: str) -> None:
    if not isinstance(value, str) or not HEX40.fullmatch(value):
        fail(f"{label} is not an immutable 40-character commit SHA: {value!r}")


def validate_lock(lock: dict) -> None:
    downstream = lock.get("android_downstream", {})
    validate_hex("android_downstream.commit", downstream.get("commit", ""))

    for lane in ("python", "godot"):
        spec = downstream.get(lane, {})
        validate_hex(f"android_downstream.{lane}.upstream_commit", spec.get("upstream_commit", ""))
        sha256 = spec.get("source_sha256", "")
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            fail(f"android_downstream.{lane}.source_sha256 must be a SHA-256")

    p4a = lock.get("android_packaging", {})
    validate_hex("android_packaging.commit", p4a.get("commit", ""))

    actions = lock.get("github_actions", {})
    if not actions:
        fail("github_actions allowlist is empty")
    for repo, commits in actions.items():
        if not re.fullmatch(r"[^/\s]+/[^/\s]+", repo):
            fail(f"invalid action repository key: {repo}")
        if not commits:
            fail(f"no approved commits for {repo}")
        for commit in commits:
            validate_hex(f"github_actions.{repo}", commit)


def validate_workflows(lock: dict) -> None:
    allow = {
        repo: set(commits)
        for repo, commits in lock.get("github_actions", {}).items()
    }
    workflow_dir = ROOT / ".github" / "workflows"
    for path in sorted(workflow_dir.glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        for ref in USES.findall(text):
            if ref.startswith("./"):
                continue
            if "@" not in ref:
                fail(f"{path.relative_to(ROOT)} has action without ref: {ref}")
            action, commit = ref.rsplit("@", 1)
            parts = action.split("/")
            if len(parts) < 2:
                fail(f"{path.relative_to(ROOT)} invalid external action: {ref}")
            repo = "/".join(parts[:2])
            if repo not in allow:
                fail(f"{path.relative_to(ROOT)} uses unapproved action repository: {repo}")
            validate_hex(f"{path.relative_to(ROOT)} action ref", commit)
            if commit not in allow[repo]:
                fail(f"{path.relative_to(ROOT)} uses unapproved commit for {repo}: {commit}")


def validate_android_vendor_lane(lock: dict) -> None:
    bootstrap = ROOT / "samsung-sm-x400" / "kai9000_dev" / "scripts" / "bootstrap-termux.sh"
    text = bootstrap.read_text(encoding="utf-8")
    required = ("x11-repo", "python", "godot")
    for token in required:
        if token not in text:
            fail(f"SM-X400 bootstrap does not select Android downstream package: {token}")

    p4a_version = lock["android_packaging"]["package_version"]
    req = ROOT / "templates" / "python3-apk" / "requirements-build.txt"
    if req.exists():
        req_text = req.read_text(encoding="utf-8")
        if f"python-for-android=={p4a_version}" not in req_text:
            fail(f"python-for-android must remain pinned to {p4a_version}")


def validate_no_mutable_github_vcs() -> None:
    suffixes = {".txt", ".toml", ".yml", ".yaml", ".json", ".sh", ".py"}
    skipped = {".git", "node_modules", "build", "dist", ".venv"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        if any(part in skipped for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        match = MUTABLE_VCS.search(text)
        if match:
            fail(f"mutable GitHub VCS dependency in {path.relative_to(ROOT)}: @{match.group(1)}")


def main() -> int:
    lock = load_lock()
    validate_lock(lock)
    validate_workflows(lock)
    validate_android_vendor_lane(lock)
    validate_no_mutable_github_vcs()
    print("OSS_VENDOR_SANITY_GREEN")
    print(f"lock={LOCK_PATH.relative_to(ROOT)}")
    print(f"downstream={lock['android_downstream']['repository']}@{lock['android_downstream']['commit']}")
    print(f"python={lock['android_downstream']['python']['version']}")
    print(f"godot={lock['android_downstream']['godot']['version']}")
    print(f"p4a={lock['android_packaging']['package_version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
