#!/usr/bin/env python3
"""Install and run safe Termux:Widget controls for Project Hydra services."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import signal
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


HYDRA_HOME = Path(os.environ.get("HYDRA_HOME", str(Path.home())))
PREFIX = Path(os.environ.get("PREFIX", os.environ.get("HYDRA_PREFIX", "/data/data/com.termux/files/usr")))
BIN_DIR = HYDRA_HOME / ".local/bin"
STATE_DIR = HYDRA_HOME / ".local/state/hydra-services"
LOG_DIR = STATE_DIR / "logs"
TASK_DIR = HYDRA_HOME / ".shortcuts/tasks"
INSTALLED_SCRIPT = BIN_DIR / "hydra-services"
STATE_FILE = STATE_DIR / "state.json"
LOCK_FILE = STATE_DIR / "control.lock"
DISPLAY = ":1"
PORTS = {"axs": 8767, "vnc": 5901, "websocket": 6080, "cockpit": 8787}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def which_any(*names: str) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.35):
            return True
    except OSError:
        return False


def wait_for_port(port: int, expected: bool, timeout: float = 12.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_open(port) is expected:
            return True
        time.sleep(0.25)
    return port_open(port) is expected


def load_state() -> dict[str, object]:
    try:
        value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {"services": {}}
    except (OSError, json.JSONDecodeError):
        return {"services": {}}


def save_state(state: dict[str, object]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    STATE_FILE.chmod(0o600)


def process_matches(pid: int, executable: str) -> bool:
    try:
        raw = (Path("/proc") / str(pid) / "cmdline").read_bytes()
    except OSError:
        return False
    expected = Path(executable).name.encode()
    return expected in raw.split(b"\0") or expected in raw


def lock_control():
    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    handle = LOCK_FILE.open("a+", encoding="utf-8")
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    return handle


def log_handle(name: str):
    LOG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = LOG_DIR / f"{name}.log"
    return path, path.open("ab", buffering=0)


def start_background(name: str, command: list[str], port: int, state: dict[str, object]) -> dict[str, object]:
    if port_open(port):
        return {"service": name, "state": "already_listening", "port": port}

    path, log = log_handle(name)
    try:
        process = subprocess.Popen(
            command,
            cwd=HYDRA_HOME,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    finally:
        log.close()

    services = state.setdefault("services", {})
    assert isinstance(services, dict)
    services[name] = {
        "pid": process.pid,
        "executable": command[0],
        "port": port,
        "started_at": now(),
    }
    save_state(state)
    healthy = wait_for_port(port, True)
    return {
        "service": name,
        "state": "running" if healthy else "failed_health_check",
        "port": port,
        "pid": process.pid,
        "log": str(path),
    }


def run_quiet(command: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)


def acquire_wake_lock() -> dict[str, object]:
    command = which_any("termux-wake-lock")
    if not command:
        return {"wake_lock": "unavailable"}
    result = run_quiet([command])
    return {"wake_lock": "held" if result.returncode == 0 else "failed"}


def start_vnc() -> dict[str, object]:
    if port_open(PORTS["vnc"]):
        return {"service": "vnc", "state": "already_listening", "port": PORTS["vnc"]}
    vncserver = which_any("vncserver")
    if not vncserver:
        return {"service": "vnc", "state": "missing_command"}
    geometry = os.environ.get("HYDRA_VNC_GEOMETRY", "1280x720")
    result = run_quiet(
        [vncserver, DISPLAY, "-localhost", "yes", "-geometry", geometry, "-depth", "24"],
        timeout=30,
    )
    healthy = wait_for_port(PORTS["vnc"], True)
    return {
        "service": "vnc",
        "state": "running" if healthy else "failed_health_check",
        "port": PORTS["vnc"],
        "returncode": result.returncode,
        "message": (result.stderr or result.stdout)[-1200:].strip(),
    }


def start_all() -> dict[str, object]:
    with lock_control():
        state = load_state()
        results: list[dict[str, object]] = [acquire_wake_lock()]

        axs = which_any("axs")
        if axs:
            results.append(start_background("axs", [axs, "-p", str(PORTS["axs"])], PORTS["axs"], state))
        else:
            results.append({"service": "axs", "state": "missing_command"})

        installed_cockpit = BIN_DIR / "hydra-cockpit"
        cockpit = str(installed_cockpit) if installed_cockpit.is_file() else which_any("hydra-cockpit")
        if cockpit:
            results.append(start_background("cockpit", [cockpit], PORTS["cockpit"], state))
        else:
            results.append({"service": "cockpit", "state": "missing_command"})

        results.append(start_vnc())

        if port_open(PORTS["vnc"]):
            proxy = which_any("websockify_rs", "websockify-rs")
            if proxy:
                results.append(
                    start_background(
                        "websocket",
                        [proxy, "127.0.0.1:6080", "127.0.0.1:5901"],
                        PORTS["websocket"],
                        state,
                    )
                )
            else:
                results.append({"service": "websocket", "state": "missing_command"})
        else:
            results.append({"service": "websocket", "state": "blocked_by_vnc"})

        state["last_start"] = now()
        save_state(state)
        return {"action": "on", "results": results, "status": status_report()}


def stop_owned(name: str, state: dict[str, object]) -> dict[str, object]:
    services = state.get("services", {})
    record = services.get(name) if isinstance(services, dict) else None
    if not isinstance(record, dict):
        return {"service": name, "state": "not_owned"}
    pid = record.get("pid")
    executable = record.get("executable")
    if not isinstance(pid, int) or not isinstance(executable, str) or not process_matches(pid, executable):
        if isinstance(services, dict):
            services.pop(name, None)
        return {"service": name, "state": "stale_pid_ignored"}
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    for _ in range(20):
        if not process_matches(pid, executable):
            break
        time.sleep(0.2)
    if isinstance(services, dict):
        services.pop(name, None)
    return {"service": name, "state": "stopped_or_exited", "pid": pid}


def stop_all() -> dict[str, object]:
    with lock_control():
        state = load_state()
        results = [
            stop_owned("websocket", state),
            stop_owned("cockpit", state),
            stop_owned("axs", state),
        ]

        vncserver = which_any("vncserver")
        if vncserver:
            result = run_quiet([vncserver, "-kill", DISPLAY])
            results.append({"service": "vnc", "state": "stop_requested", "returncode": result.returncode})
        else:
            results.append({"service": "vnc", "state": "missing_command"})

        wake_unlock = which_any("termux-wake-unlock")
        if wake_unlock:
            run_quiet([wake_unlock])
        state["last_stop"] = now()
        save_state(state)
        return {"action": "off", "results": results, "status": status_report()}


def status_report() -> dict[str, object]:
    state = load_state()
    services = state.get("services", {})
    ownership: dict[str, str] = {}
    if isinstance(services, dict):
        for name, record in services.items():
            if isinstance(record, dict) and isinstance(record.get("pid"), int) and isinstance(record.get("executable"), str):
                ownership[name] = "owned" if process_matches(record["pid"], record["executable"]) else "stale"
    return {
        "action": "status",
        "ports": {name: {"port": port, "listening": port_open(port)} for name, port in PORTS.items()},
        "ownership": ownership,
        "state_file": str(STATE_FILE),
    }


def wrapper(action: str) -> str:
    return f"#!{PREFIX}/bin/sh\nexec {INSTALLED_SCRIPT} {action}\n"


def install(start: bool) -> dict[str, object]:
    for directory in (BIN_DIR, STATE_DIR, LOG_DIR, TASK_DIR):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)

    source = Path(__file__).resolve()
    if source != INSTALLED_SCRIPT.resolve(strict=False):
        shutil.copyfile(source, INSTALLED_SCRIPT)
    INSTALLED_SCRIPT.chmod(0o700)

    installed: list[str] = []
    for filename, action in (
        ("HYDRA-ON", "on"),
        ("HYDRA-STATUS", "status"),
        ("HYDRA-OFF", "off"),
    ):
        target = TASK_DIR / filename
        target.write_text(wrapper(action), encoding="utf-8")
        target.chmod(0o700)
        installed.append(str(target))

    am = which_any("am")
    if am:
        run_quiet([am, "broadcast", "-a", "com.termux.widget.ACTION_REFRESH_WIDGET"])

    result: dict[str, object] = {
        "action": "install",
        "installed_script": str(INSTALLED_SCRIPT),
        "widget_tasks": installed,
    }
    if start:
        result["start"] = start_all()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("--start", action="store_true")
    subparsers.add_parser("on")
    subparsers.add_parser("status")
    subparsers.add_parser("off")
    args = parser.parse_args()

    try:
        if args.action == "install":
            result = install(args.start)
        elif args.action == "on":
            result = start_all()
        elif args.action == "off":
            result = stop_all()
        else:
            result = status_report()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"action": args.action, "error": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
