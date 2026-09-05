from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

TERMUX_PACKAGE = "com.termux"
APP_PACKAGE = "art.eggiebagelface.videoforge.dev"


def run(adb: str, *args: str, timeout: float = 8.0) -> dict[str, object]:
    try:
        started = time.perf_counter()
        result = subprocess.run(
            [adb, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "code": result.returncode,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": type(exc).__name__}


def shell(adb: str, *args: str, timeout: float = 8.0) -> dict[str, object]:
    return run(adb, "shell", *args, timeout=timeout)


def http_probe(url: str, timeout: float = 2.0) -> dict[str, object]:
    started = time.perf_counter()
    try:
        with urlopen(url, timeout=timeout) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            return {
                "ok": response.status == 200,
                "status": response.status,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "body": body[:1000],
            }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": type(exc).__name__,
        }


def prop(adb: str, name: str) -> str:
    result = shell(adb, "getprop", name)
    return str(result.get("stdout", "")) if result.get("ok") else ""


def package_installed(adb: str, package: str) -> bool:
    return bool(shell(adb, "pm", "path", package).get("ok"))


def background_state(adb: str, package: str) -> dict[str, object]:
    run_background = shell(adb, "cmd", "appops", "get", package, "RUN_IN_BACKGROUND")
    run_any = shell(adb, "cmd", "appops", "get", package, "RUN_ANY_IN_BACKGROUND")
    standby = shell(adb, "am", "get-standby-bucket", package)
    run_background_text = str(run_background.get("stdout", ""))
    run_any_text = str(run_any.get("stdout", ""))
    standby_text = str(standby.get("stdout", "")).strip().lower()
    return {
        "run_in_background": run_background_text,
        "run_any_in_background": run_any_text,
        "standby_bucket": standby_text,
        "run_in_background_allow": "allow" in run_background_text.lower(),
        "run_any_in_background_allow": "allow" in run_any_text.lower(),
        "standby_active": standby_text in {"10", "active"} or standby_text.endswith(": 10"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Samsung SM-X400 ADB smoke test")
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--health-port", type=int, default=18000)
    parser.add_argument("--ollama-port", type=int, default=18114)
    parser.add_argument("--output", default="build/samsung-device-smoke.json")
    args = parser.parse_args()

    adb = args.adb
    state = run(adb, "get-state")
    if not state.get("ok") or str(state.get("stdout", "")) != "device":
        raise SystemExit("SAMSUNG_DEVICE_SMOKE_FAIL: adb device unavailable")

    device = {
        "manufacturer": prop(adb, "ro.product.manufacturer"),
        "model": prop(adb, "ro.product.model"),
        "android_release": prop(adb, "ro.build.version.release"),
        "sdk": prop(adb, "ro.build.version.sdk"),
        "abi": prop(adb, "ro.product.cpu.abi"),
        "vulkan_version": prop(adb, "ro.hardware.vulkan.version"),
        "vulkan_level": prop(adb, "ro.hardware.vulkan.level"),
    }

    packages = {
        TERMUX_PACKAGE: package_installed(adb, TERMUX_PACKAGE),
        APP_PACKAGE: package_installed(adb, APP_PACKAGE),
    }
    background = {
        TERMUX_PACKAGE: background_state(adb, TERMUX_PACKAGE),
        APP_PACKAGE: background_state(adb, APP_PACKAGE),
    }

    webview = shell(adb, "dumpsys", "webviewupdate", timeout=12)
    device_policy = shell(adb, "dumpsys", "device_policy", timeout=12)

    run(adb, "forward", f"tcp:{args.health_port}", "tcp:8000")
    run(adb, "forward", f"tcp:{args.ollama_port}", "tcp:11434")
    try:
        fastapi = http_probe(f"http://127.0.0.1:{args.health_port}/api/health")
        ollama = http_probe(f"http://127.0.0.1:{args.ollama_port}/api/tags")
    finally:
        run(adb, "forward", "--remove", f"tcp:{args.health_port}")
        run(adb, "forward", "--remove", f"tcp:{args.ollama_port}")

    failures: list[str] = []
    if device["manufacturer"].lower() != "samsung":
        failures.append("not_samsung")
    if not device["vulkan_version"]:
        failures.append("vulkan_property_missing")
    if not packages[TERMUX_PACKAGE]:
        failures.append("termux_missing")
    if not packages[APP_PACKAGE]:
        failures.append("video_forge_missing")
    if not fastapi.get("ok"):
        failures.append("fastapi_unhealthy")

    for package, guard in background.items():
        if not guard["run_in_background_allow"]:
            failures.append(f"{package}:run_in_background_not_allow")
        if not guard["run_any_in_background_allow"]:
            failures.append(f"{package}:run_any_in_background_not_allow")
        if not guard["standby_active"]:
            failures.append(f"{package}:standby_not_active")

    payload = {
        "schema": "video-forge.samsung-device-smoke.v1",
        "timestamp_unix": int(time.time()),
        "device": device,
        "packages": packages,
        "background_guard": background,
        "webview": {
            "ok": bool(webview.get("ok")),
            "summary": str(webview.get("stdout", ""))[:5000],
        },
        "device_policy": {
            "ok": bool(device_policy.get("ok")),
            "summary": str(device_policy.get("stdout", ""))[:5000],
        },
        "services": {"fastapi": fastapi, "ollama_optional": ollama},
        "failures": failures,
        "ok": not failures,
    }

    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))

    if failures:
        print("SAMSUNG_DEVICE_SMOKE_RED")
        return 2
    print("SAMSUNG_DEVICE_SMOKE_GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
