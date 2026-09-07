#!/usr/bin/env python3
"""Single Python orchestration layer behind the npm Samsung SM-X400 build wizard."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPS = ROOT / "apps"
WIDGET_BUILDER = ROOT / "scripts" / "sm_x400_widget_build.py"
SHIZUKU_SANITY = ROOT / "scripts" / "sm_x400_shizuku_sanity.py"


def frontend_step() -> dict[str, object]:
    return {
        "name": "frontend",
        "cwd": str(APPS),
        "command": ["npm", "run", "build", "--workspace=video-forge-ui"],
    }


def widget_step() -> dict[str, object]:
    return {
        "name": "widget",
        "cwd": str(ROOT),
        "command": [sys.executable, str(WIDGET_BUILDER), "--build"],
    }


def shizuku_step() -> dict[str, object]:
    return {
        "name": "shizuku",
        "cwd": str(ROOT),
        "command": [sys.executable, str(SHIZUKU_SANITY)],
    }


def choose_interactive() -> tuple[str, bool, bool]:
    print("Samsung SM-X400 build wizard")
    print("  1) Frontend only (default)")
    print("  2) Widget only")
    print("  3) Candidate frontend + optional widget")
    print("  4) Candidate + widget + Shizuku broker")
    print("  5) Shizuku broker contract check")
    print("  6) Quit")
    choice = input("Select [1]: ").strip() or "1"
    if choice == "2":
        return "widget", True, False
    if choice == "3":
        include = input("Include optional Termux widget bundle? [y/N]: ").strip().lower() in {"y", "yes"}
        return "candidate", include, False
    if choice == "4":
        return "candidate", True, True
    if choice == "5":
        return "shizuku", False, True
    if choice == "6":
        return "quit", False, False
    return "frontend", False, False


def plan(mode: str, with_widget: bool, with_shizuku: bool) -> list[dict[str, object]]:
    if mode == "widget":
        return [widget_step()]
    if mode == "shizuku":
        return [shizuku_step()]
    if mode == "candidate":
        steps = [frontend_step()]
        if with_shizuku:
            steps.append(shizuku_step())
        if with_widget or with_shizuku:
            steps.append(widget_step())
        return steps
    if mode == "frontend":
        return [frontend_step()]
    return []


def validate_tools(steps: list[dict[str, object]]) -> list[str]:
    missing: list[str] = []
    for step in steps:
        command = step["command"]
        assert isinstance(command, list) and command
        executable = str(command[0])
        if Path(executable).is_absolute():
            if not Path(executable).exists():
                missing.append(executable)
        elif shutil.which(executable) is None:
            missing.append(executable)
    return sorted(set(missing))


def execute(steps: list[dict[str, object]]) -> int:
    for step in steps:
        name = str(step["name"])
        cwd = str(step["cwd"])
        command = [str(value) for value in step["command"]]
        print(f"[wizard] {name}: {' '.join(command)}")
        result = subprocess.run(command, cwd=cwd, check=False)
        if result.returncode != 0:
            print(f"[wizard] {name} failed with exit code {result.returncode}", file=sys.stderr)
            return result.returncode
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--frontend", action="store_true", help="build only the Vue frontend")
    modes.add_argument("--widget", action="store_true", help="build only the optional widget bundle")
    modes.add_argument("--shizuku", action="store_true", help="validate only the optional Shizuku broker contract")
    modes.add_argument("--candidate", action="store_true", help="build the frontend candidate; widget and Shizuku stay opt-in")
    parser.add_argument("--with-widget", action="store_true", help="include the widget with --candidate")
    parser.add_argument("--with-shizuku", action="store_true", help="validate Shizuku and include the widget with --candidate")
    parser.add_argument("--dry-run", action="store_true", help="print the deterministic plan without executing it")
    args = parser.parse_args()

    if args.with_widget and not args.candidate:
        parser.error("--with-widget is valid only with --candidate")
    if args.with_shizuku and not args.candidate:
        parser.error("--with-shizuku is valid only with --candidate")

    if args.frontend:
        mode, with_widget, with_shizuku = "frontend", False, False
    elif args.widget:
        mode, with_widget, with_shizuku = "widget", True, False
    elif args.shizuku:
        mode, with_widget, with_shizuku = "shizuku", False, True
    elif args.candidate:
        mode = "candidate"
        with_widget = args.with_widget or args.with_shizuku
        with_shizuku = args.with_shizuku
    elif sys.stdin.isatty():
        mode, with_widget, with_shizuku = choose_interactive()
    else:
        mode, with_widget, with_shizuku = "frontend", False, False

    if mode == "quit":
        return 0

    steps = plan(mode, with_widget, with_shizuku)
    missing = validate_tools(steps)
    result = {
        "mode": mode,
        "withWidget": with_widget,
        "withShizuku": with_shizuku,
        "widgetOptional": True,
        "shizukuOptional": True,
        "preferredShizukuMode": "wireless-adb",
        "steps": steps,
        "missingTools": missing,
    }

    if args.dry_run:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if not missing else 2

    if missing:
        print(json.dumps(result, indent=2, sort_keys=True), file=sys.stderr)
        return 2

    return execute(steps)


if __name__ == "__main__":
    raise SystemExit(main())
