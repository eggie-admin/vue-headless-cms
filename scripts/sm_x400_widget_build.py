#!/usr/bin/env python3
"""Validate and stage the optional Samsung SM-X400 frontend widget bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIDGET_ROOT = ROOT / "samsung-sm-x400" / "frontend" / "widget"
MANIFEST_PATH = WIDGET_ROOT / "widget.manifest.json"
DIST_ROOT = ROOT / "dist" / "samsung-sm-x400" / "frontend" / "widget"


def load_manifest() -> dict[str, object]:
    value = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("widget.manifest.json must contain a JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(manifest: dict[str, object]) -> list[str]:
    errors: list[str] = []

    if manifest.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    if manifest.get("id") != "samsung-sm-x400.frontend.widget":
        errors.append("unexpected widget id")
    if manifest.get("optional") is not True:
        errors.append("widget lane must remain optional")

    target = manifest.get("target")
    if not isinstance(target, dict) or target.get("model") != "SM-X400":
        errors.append("target.model must be SM-X400")

    source = manifest.get("source")
    if not isinstance(source, dict):
        errors.append("source metadata is required")
    else:
        commit = source.get("mergeCommit")
        if not isinstance(commit, str) or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit.lower()):
            errors.append("source.mergeCommit must be a 40-character Git SHA")

    build_dependencies = manifest.get("buildDependencies")
    if not isinstance(build_dependencies, dict):
        errors.append("buildDependencies must be an object")
    elif build_dependencies.get("npmPackages") != []:
        errors.append("widget build must not add npm package dependencies")

    runtime_dependencies = manifest.get("runtimeDependencies")
    if not isinstance(runtime_dependencies, dict):
        errors.append("runtimeDependencies must be an object")
    else:
        required_apps = runtime_dependencies.get("requiredAndroidApps")
        if required_apps != ["Termux", "Termux:Widget"]:
            errors.append("requiredAndroidApps must remain Termux + Termux:Widget")

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        errors.append("manifest files list is required")
    else:
        for item in files:
            if (
                not isinstance(item, str)
                or not item
                or item.startswith(("/", "\\"))
                or "\\" in item
                or ".." in Path(item).parts
            ):
                errors.append(f"unsafe widget file entry: {item!r}")
                continue
            path = WIDGET_ROOT / item
            if not path.is_file():
                errors.append(f"missing widget file: {item}")

    source_file = WIDGET_ROOT / "hydra_widget_setup.py"
    if source_file.is_file():
        try:
            compile(source_file.read_text(encoding="utf-8"), str(source_file), "exec")
        except SyntaxError as exc:
            errors.append(f"hydra_widget_setup.py does not compile: {exc}")

    return errors


def runtime_report(manifest: dict[str, object]) -> dict[str, object]:
    runtime_dependencies = manifest.get("runtimeDependencies")
    if not isinstance(runtime_dependencies, dict):
        return {"required": {}, "optional": {}}

    required = runtime_dependencies.get("requiredCommands", [])
    optional = runtime_dependencies.get("optionalCommands", [])

    def resolve(values: object) -> dict[str, bool]:
        if not isinstance(values, list):
            return {}
        return {str(name): shutil.which(str(name)) is not None for name in values}

    return {"required": resolve(required), "optional": resolve(optional)}


def stage(manifest: dict[str, object]) -> dict[str, str]:
    if DIST_ROOT.exists():
        shutil.rmtree(DIST_ROOT)
    DIST_ROOT.mkdir(parents=True, exist_ok=True)

    files = manifest["files"]
    assert isinstance(files, list)
    hashes: dict[str, str] = {}
    for item in sorted(str(value) for value in files):
        source = WIDGET_ROOT / item
        target = DIST_ROOT / item
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        hashes[item] = sha256(target)

    build_manifest = {
        "schemaVersion": 1,
        "id": manifest["id"],
        "optional": True,
        "source": manifest["source"],
        "files": hashes,
    }
    (DIST_ROOT / "build-manifest.json").write_text(
        json.dumps(build_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return hashes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate the widget source contract only")
    mode.add_argument("--build", action="store_true", help="validate and stage the deterministic widget bundle")
    parser.add_argument("--runtime-check", action="store_true", help="report local command availability without changing dependency planes")
    args = parser.parse_args()

    try:
        manifest = load_manifest()
        errors = validate(manifest)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1

    report: dict[str, object] = {
        "ok": not errors,
        "widgetRoot": str(WIDGET_ROOT.relative_to(ROOT)),
        "optional": manifest.get("optional"),
        "errors": errors,
    }

    if args.runtime_check:
        report["runtime"] = runtime_report(manifest)

    if errors:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    if args.build:
        report["staged"] = str(DIST_ROOT.relative_to(ROOT))
        report["files"] = stage(manifest)

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
