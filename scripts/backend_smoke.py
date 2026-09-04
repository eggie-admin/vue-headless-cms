from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
PORT = int(os.getenv("BACKEND_SMOKE_PORT", "8765"))
BASE_URL = f"http://127.0.0.1:{PORT}"
SMOKE_TOKEN = "ci-smoke-token"


def request_json(
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    token: str | None = None,
) -> tuple[int, dict[str, object]]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-Cathedral-Token"] = token
    request = Request(BASE_URL + path, data=data, headers=headers, method=method)
    with urlopen(request, timeout=2) as response:
        body = json.loads(response.read().decode("utf-8"))
        return response.status, body


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cathedral-backend-smoke-") as tmp:
        tmp_path = Path(tmp)
        log_path = tmp_path / "backend.log"
        env = os.environ.copy()
        env["CMS_STATE_DB"] = str(tmp_path / "cms.sqlite3")
        env["CMS_WRITE_TOKEN_FILE"] = str(tmp_path / "cms-token.txt")
        env["VIDEO_FORGE_CMS_TOKEN"] = SMOKE_TOKEN

        command = [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--app-dir",
            str(SERVER),
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
            "--log-level",
            "warning",
        ]

        with log_path.open("w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
            )

            try:
                health: dict[str, object] | None = None
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        break
                    try:
                        status, health = request_json("/api/health")
                        if status == 200:
                            break
                    except (URLError, TimeoutError, ConnectionError):
                        time.sleep(0.25)
                else:
                    raise RuntimeError("backend did not become healthy before smoke deadline")

                if process.poll() is not None:
                    raise RuntimeError("backend exited before health check")
                if health is None or health.get("ok") is not True or health.get("cms") != "persistent":
                    raise RuntimeError(f"unexpected health payload: {health!r}")

                status, documents = request_json("/api/cms/documents")
                seeded = documents.get("documents")
                if status != 200 or not isinstance(seeded, list) or len(seeded) < 3:
                    raise RuntimeError(f"CMS seed smoke failed: {documents!r}")

                payload = {
                    "kind": "content",
                    "title": "Backend Smoke Document",
                    "payload": {"status": "green"},
                }

                try:
                    request_json(
                        "/api/cms/documents/backend-smoke",
                        method="PUT",
                        payload=payload,
                    )
                except HTTPError as exc:
                    if exc.code != 401:
                        raise RuntimeError(f"unauthenticated CMS write returned {exc.code}, expected 401") from exc
                else:
                    raise RuntimeError("unauthenticated CMS write unexpectedly succeeded")

                status, created = request_json(
                    "/api/cms/documents/backend-smoke",
                    method="PUT",
                    payload=payload,
                    token=SMOKE_TOKEN,
                )
                document = created.get("document")
                if (
                    status != 200
                    or not isinstance(document, dict)
                    or document.get("id") != "backend-smoke"
                    or document.get("revision") != 1
                ):
                    raise RuntimeError(f"authenticated CMS write smoke failed: {created!r}")

                status, loaded = request_json("/api/cms/documents/backend-smoke")
                loaded_document = loaded.get("document")
                if status != 200 or not isinstance(loaded_document, dict) or loaded_document.get("revision") != 1:
                    raise RuntimeError(f"CMS read-after-write smoke failed: {loaded!r}")

                print(
                    "BACKEND_SMOKE_GREEN "
                    f"health={health.get('ok')} cms={health.get('cms')} "
                    f"seeded={len(seeded)} write_auth=401 authenticated_revision=1"
                )
                return 0
            except Exception:
                log_file.flush()
                if log_path.is_file():
                    print("--- backend smoke log ---", file=sys.stderr)
                    print(log_path.read_text(encoding="utf-8", errors="replace"), file=sys.stderr)
                raise
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
