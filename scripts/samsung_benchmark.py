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
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency gate
    raise SystemExit("PyYAML is required. Install the Video Forge server dependencies first.") from exc

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "infra/samsung/samsung-benchmark.yml"


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


def load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("benchmark YAML must contain one mapping at the root")
    return payload


def validate_config(config: dict[str, Any]) -> None:
    required = ["schema", "policy", "output", "android", "services", "profiles", "benchmarks", "thresholds"]
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"benchmark YAML missing required keys: {', '.join(missing)}")

    if config["schema"] != "video-forge.samsung-benchmark.config.v1":
        raise ValueError("unsupported benchmark config schema")
    if config["policy"].get("config_is_authoritative") is not True:
        raise ValueError("config_is_authoritative must be true")
    if config["policy"].get("public_network_targets") is not False:
        raise ValueError("public network benchmark targets are forbidden")
    if config["policy"].get("execute_model_output") is not False:
        raise ValueError("benchmark must not execute model output")

    for name, service in config["services"].items():
        url = str(service.get("url", ""))
        parsed = urlparse(url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError(f"service {name} must remain loopback HTTP")
        if not isinstance(service.get("timeout_s"), (int, float)) or service["timeout_s"] <= 0:
            raise ValueError(f"service {name} timeout_s must be positive")

    for profile in ("smoke", "full"):
        if profile not in config["profiles"]:
            raise ValueError(f"missing profile: {profile}")


def getprop(name: str, timeout: float) -> str:
    result = run(["/system/bin/getprop", name], timeout=timeout)
    return str(result.get("stdout", "")) if result.get("ok") else ""


def http_probe(url: str, timeout: float = 2.0, expected_status: int = 200) -> dict[str, object]:
    started = time.perf_counter()
    try:
        with urlopen(url, timeout=timeout) as response:
            body = response.read(8192).decode("utf-8", errors="replace")
            return {
                "ok": response.status == expected_status,
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


def webview_snapshot(timeout: float) -> dict[str, object]:
    dumpsys = run(["/system/bin/dumpsys", "webviewupdate"], timeout=timeout)
    text = str(dumpsys.get("stdout", ""))
    match = re.search(r"Current WebView package.*?\(([^)]+)\)", text)
    if not match:
        match = re.search(r"Current WebView package.*?:\s*(.+)", text)
    return {
        "ok": bool(dumpsys.get("ok")),
        "current": match.group(1).strip() if match else "unknown",
    }


def read_text_snapshot(path: str, limit: int = 8000) -> dict[str, object]:
    target = Path(path)
    try:
        return {"ok": True, "text": target.read_text(encoding="utf-8", errors="replace")[:limit].strip()}
    except OSError as exc:
        return {"ok": False, "error": type(exc).__name__}


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def system_snapshot(config: dict[str, Any]) -> dict[str, object]:
    spec = config["system_snapshot"]
    command_timeout = float(config["commands"].get("runtime_timeout_s", 3))
    thermal_timeout = float(config["commands"].get("thermal_timeout_s", 4))

    battery_result = run([str(x) for x in spec["battery"]["command"]], timeout=command_timeout)
    battery = parse_key_values(str(battery_result.get("stdout", ""))) if battery_result.get("ok") else battery_result

    memory_raw = read_text_snapshot(str(spec["memory"]["path"]))
    memory = parse_key_values(str(memory_raw.get("text", ""))) if memory_raw.get("ok") else memory_raw

    thermal_values: list[dict[str, object]] = []
    max_zones = int(spec["thermal"].get("max_zones", 32))
    for path in sorted(Path("/").glob(str(spec["thermal"]["glob"]).lstrip("/")))[:max_zones]:
        started = time.perf_counter()
        try:
            raw = path.read_text(encoding="utf-8", errors="replace").strip()
            value = float(raw)
            celsius = value / 1000.0 if abs(value) > 200 else value
            thermal_values.append({"path": str(path), "celsius": round(celsius, 2)})
        except (OSError, ValueError):
            continue
        if time.perf_counter() - started > thermal_timeout:
            break

    return {
        "battery": battery,
        "memory": memory,
        "storage": run([str(x) for x in spec["storage"]["command"]], timeout=command_timeout),
        "kernel": run([str(x) for x in spec["kernel"]["command"]], timeout=command_timeout),
        "uptime": read_text_snapshot(str(spec["uptime"]["path"]), limit=1000),
        "loadavg": read_text_snapshot(str(spec["loadavg"]["path"]), limit=1000),
        "thermal": thermal_values,
        "cpu_count": os.cpu_count(),
    }


def cpu_hash_benchmark(spec: dict[str, Any]) -> dict[str, object]:
    seed = str(spec["block_seed"]).encode("utf-8")
    block = seed * int(spec["block_repeat"])
    target_bytes = int(spec["total_mib"]) * 1024 * 1024
    total = 0
    digest = hashlib.sha256()
    started = time.perf_counter()
    while total < target_bytes:
        digest.update(block)
        total += len(block)
    elapsed = max(time.perf_counter() - started, 1e-9)
    return {
        "bytes": total,
        "elapsed_ms": round(elapsed * 1000, 2),
        "mb_per_s": round((total / 1024 / 1024) / elapsed, 2),
        "digest_prefix": digest.hexdigest()[:12],
    }


def disk_benchmark(spec: dict[str, Any]) -> dict[str, object]:
    block_mib = int(spec["block_mib"])
    total_mib = int(spec["total_mib"])
    payload = b"0" * (block_mib * 1024 * 1024)
    iterations = max(1, total_mib // block_mib)
    with tempfile.NamedTemporaryFile(prefix="cathedral-bench-", delete=False) as handle:
        path = Path(handle.name)
        started = time.perf_counter()
        for _ in range(iterations):
            handle.write(payload)
        handle.flush()
        if bool(spec.get("fsync", True)):
            os.fsync(handle.fileno())
        elapsed = max(time.perf_counter() - started, 1e-9)
    path.unlink(missing_ok=True)
    written_mib = iterations * block_mib
    return {
        "bytes": written_mib * 1024 * 1024,
        "elapsed_ms": round(elapsed * 1000, 2),
        "mb_per_s": round(written_mib / elapsed, 2),
        "fsync": bool(spec.get("fsync", True)),
    }


def ffmpeg_benchmark(spec: dict[str, Any]) -> dict[str, object]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"ok": False, "reason": "ffmpeg_missing"}
    extension = str(spec.get("extension", "mp4")).lstrip(".")
    with tempfile.TemporaryDirectory(prefix="cathedral-ffmpeg-") as tmp:
        target = str(Path(tmp) / f"bench.{extension}")
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            str(spec["source"]),
            "-t",
            str(spec["duration_s"]),
            "-c:v",
            str(spec["codec"]),
            "-preset",
            str(spec["preset"]),
            "-crf",
            str(spec["crf"]),
            "-pix_fmt",
            str(spec["pixel_format"]),
            target,
        ]
        result = run(command, timeout=float(spec["timeout_s"]))
        if Path(target).is_file():
            result["output_bytes"] = Path(target).stat().st_size
        result["command_profile"] = {
            "source": spec["source"],
            "duration_s": spec["duration_s"],
            "codec": spec["codec"],
            "preset": spec["preset"],
            "crf": spec["crf"],
            "pixel_format": spec["pixel_format"],
        }
        return result


def evaluate(report: dict[str, Any], config: dict[str, Any], profile: str) -> dict[str, object]:
    thresholds = config["thresholds"][profile]
    failures: list[str] = []

    if bool(thresholds.get("fastapi_required")) and not report["services"]["fastapi"].get("ok"):
        failures.append("fastapi_unhealthy")

    for name, service in config["services"].items():
        if bool(service.get(f"required_in_{profile}")) and not report["services"][name].get("ok"):
            marker = f"service_{name}_required"
            if marker not in failures and name != "fastapi":
                failures.append(marker)

    if profile == "full":
        benchmarks = report.get("benchmarks", {})
        cpu = benchmarks.get("cpu_sha256", {})
        disk = benchmarks.get("disk_write", {})
        ffmpeg = benchmarks.get("ffmpeg_h264", {})
        if float(cpu.get("mb_per_s", 0)) < float(thresholds.get("cpu_sha256_mb_s_min", 0)):
            failures.append("cpu_sha256_below_threshold")
        if float(disk.get("mb_per_s", 0)) < float(thresholds.get("disk_write_mb_s_min", 0)):
            failures.append("disk_write_below_threshold")
        if bool(thresholds.get("ffmpeg_required")) and not ffmpeg.get("ok"):
            failures.append("ffmpeg_failed")
        if float(ffmpeg.get("elapsed_ms", 0)) > float(thresholds.get("ffmpeg_max_elapsed_ms", 1e18)):
            failures.append("ffmpeg_too_slow")

    return {"ok": not failures, "failures": failures, "thresholds": thresholds}


def build_report(config: dict[str, Any], profile: str, config_path: Path) -> dict[str, object]:
    android = config["android"]
    command_cfg = config["commands"]
    getprop_timeout = float(command_cfg.get("getprop_timeout_s", 2))

    properties = {
        key: getprop(str(prop_name), timeout=getprop_timeout)
        for key, prop_name in android["properties"].items()
    }

    services = {
        name: http_probe(
            str(spec["url"]),
            timeout=float(spec["timeout_s"]),
            expected_status=int(spec.get("expected_status", 200)),
        )
        for name, spec in config["services"].items()
    }

    runtime_timeout = float(command_cfg.get("runtime_timeout_s", 3))
    runtime: dict[str, object] = {"python": platform.python_version()}
    for name, command in config["runtime_commands"].items():
        executable = str(command[0])
        runtime[name] = run([str(x) for x in command], timeout=runtime_timeout) if shutil.which(executable) else {"ok": False, "reason": f"{executable}_missing"}

    processes = {
        name: bool(run(["pgrep", "-f", str(spec["pattern"])], timeout=float(command_cfg.get("process_timeout_s", 2))).get("ok"))
        if shutil.which("pgrep")
        else False
        for name, spec in config["process_watch"].items()
    }

    vulkan_spec = config["vulkan"]
    vulkan_command = [str(x) for x in vulkan_spec["command"]]
    vulkan = {
        "version_property": properties.get("vulkan_version", ""),
        "level_property": properties.get("vulkan_level", ""),
        "vulkaninfo": run(vulkan_command, timeout=float(command_cfg.get("vulkan_timeout_s", 8)))
        if shutil.which(vulkan_command[0])
        else {"ok": False, "reason": "vulkaninfo_missing"},
    }

    report: dict[str, Any] = {
        "schema": config["output"]["schema"],
        "config_schema": config["schema"],
        "config_path": str(config_path),
        "profile": profile,
        "timestamp_unix": int(time.time()),
        "device": properties,
        "system": system_snapshot(config),
        "webview": webview_snapshot(float(command_cfg.get("webview_timeout_s", 4))),
        "vulkan": vulkan,
        "runtime": runtime,
        "services": services,
        "processes": processes,
    }

    if profile == "full":
        enabled = set(config["profiles"]["full"].get("benchmarks", []))
        report["benchmarks"] = {}
        if "cpu_sha256" in enabled:
            report["benchmarks"]["cpu_sha256"] = cpu_hash_benchmark(config["benchmarks"]["cpu_sha256"])
        if "disk_write" in enabled:
            report["benchmarks"]["disk_write"] = disk_benchmark(config["benchmarks"]["disk_write"])
        if "ffmpeg_h264" in enabled:
            report["benchmarks"]["ffmpeg_h264"] = ffmpeg_benchmark(config["benchmarks"]["ffmpeg_h264"])

    report["evaluation"] = evaluate(report, config, profile)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Samsung SM-X400 YAML-driven local benchmark")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--profile", choices=("smoke", "full"))
    legacy = parser.add_mutually_exclusive_group()
    legacy.add_argument("--smoke", action="store_true", help="compatibility alias for --profile smoke")
    legacy.add_argument("--full", action="store_true", help="compatibility alias for --profile full")
    parser.add_argument("--output")
    parser.add_argument("--validate-config", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    config = load_config(config_path)
    validate_config(config)

    if args.validate_config:
        print(f"SAMSUNG_BENCHMARK_CONFIG_GREEN path={config_path}")
        return 0

    profile = args.profile or ("full" if args.full else "smoke")
    report = build_report(config, profile, config_path)
    encoded = json.dumps(report, indent=2, sort_keys=True)

    output_value = args.output or config["output"][f"{profile}_path"]
    output = Path(str(output_value)).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)

    return 0 if report["evaluation"]["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
