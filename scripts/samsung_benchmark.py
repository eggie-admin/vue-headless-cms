from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], timeout: float = 5.0) -> dict[str, object]:
    try:
        started = time.perf_counter()
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "code": result.returncode,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            "stdout": result.stdout.strip()[:4000],
            "stderr": result.stderr.strip()[:1000],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": type(exc).__name__}


def getprop(name: str) -> str:
    result = run(["/system/bin/getprop", name], timeout=2)
    return str(result.get("stdout", "")) if result.get("ok") else ""


def http_probe(url: str, timeout: float = 2.0) -> dict[str, object]:
    started = time.perf_counter()
    try:
        with urlopen(url, timeout=timeout) as response:
            body = response.read(8192).decode("utf-8", errors="replace")
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


def webview_snapshot() -> dict[str, object]:
    dumpsys = run(["/system/bin/dumpsys", "webviewupdate"], timeout=4)
    text = str(dumpsys.get("stdout", ""))
    match = re.search(r"Current WebView package.*?\(([^)]+)\)", text)
    if not match:
        match = re.search(r"Current WebView package.*?:\s*(.+)", text)
    return {
        "ok": bool(dumpsys.get("ok")),
        "current": match.group(1).strip() if match else "unknown",
    }


def cpu_hash_benchmark() -> dict[str, object]:
    block = b"video-forge-cathedral" * 4096
    total = 0
    digest = hashlib.sha256()
    started = time.perf_counter()
    while total < 32 * 1024 * 1024:
        digest.update(block)
        total += len(block)
    elapsed = max(time.perf_counter() - started, 1e-9)
    return {
        "bytes": total,
        "mb_per_s": round((total / 1024 / 1024) / elapsed, 2),
        "digest_prefix": digest.hexdigest()[:12],
    }


def disk_benchmark() -> dict[str, object]:
    payload = b"0" * (1024 * 1024)
    with tempfile.NamedTemporaryFile(prefix="cathedral-bench-", delete=False) as handle:
        path = Path(handle.name)
        started = time.perf_counter()
        for _ in range(32):
            handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
        elapsed = max(time.perf_counter() - started, 1e-9)
    path.unlink(missing_ok=True)
    return {"bytes": 32 * 1024 * 1024, "mb_per_s": round(32 / elapsed, 2)}


def ffmpeg_benchmark() -> dict[str, object]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"ok": False, "reason": "ffmpeg_missing"}
    with tempfile.TemporaryDirectory(prefix="cathedral-ffmpeg-") as tmp:
        target = str(Path(tmp) / "bench.mp4")
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=540x960:rate=30",
            "-t",
            "2",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            target,
        ]
        result = run(command, timeout=45)
        if Path(target).is_file():
            result["output_bytes"] = Path(target).stat().st_size
        return result


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    health = http_probe("http://127.0.0.1:8000/api/health")
    ollama = http_probe("http://127.0.0.1:11434/api/tags")
    report: dict[str, object] = {
        "schema": "video-forge.samsung-benchmark.v1",
        "mode": "full" if args.full else "smoke",
        "timestamp_unix": int(time.time()),
        "device": {
            "manufacturer": getprop("ro.product.manufacturer") or platform.system(),
            "model": getprop("ro.product.model") or platform.machine(),
            "android_release": getprop("ro.build.version.release"),
            "sdk": getprop("ro.build.version.sdk"),
            "abi": getprop("ro.product.cpu.abi") or platform.machine(),
        },
        "webview": webview_snapshot(),
        "vulkan": {
            "version_property": getprop("ro.hardware.vulkan.version"),
            "level_property": getprop("ro.hardware.vulkan.level"),
            "vulkaninfo": run(["vulkaninfo", "--summary"], timeout=8) if shutil.which("vulkaninfo") else {"ok": False, "reason": "vulkaninfo_missing"},
        },
        "runtime": {
            "python": platform.python_version(),
            "node": run(["node", "--version"], timeout=2) if shutil.which("node") else {"ok": False},
            "npm": run(["npm", "--version"], timeout=2) if shutil.which("npm") else {"ok": False},
            "ffmpeg": run(["ffmpeg", "-version"], timeout=3) if shutil.which("ffmpeg") else {"ok": False},
            "godot": run(["godot", "--version"], timeout=3) if shutil.which("godot") else {"ok": False},
        },
        "services": {
            "fastapi": health,
            "ollama": ollama,
            "x11_running": bool(run(["pgrep", "-f", "termux-x11"], timeout=2).get("ok")) if shutil.which("pgrep") else False,
            "vnc_running": bool(run(["pgrep", "-f", "x11vnc|Xtigervnc"], timeout=2).get("ok")) if shutil.which("pgrep") else False,
        },
    }

    if args.full:
        report["benchmarks"] = {
            "cpu_sha256": cpu_hash_benchmark(),
            "disk_write": disk_benchmark(),
            "ffmpeg_540x960_h264": ffmpeg_benchmark(),
        }

    encoded = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)

    if not health.get("ok"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
