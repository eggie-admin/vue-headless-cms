from __future__ import annotations

import json
import pathlib
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
failures: list[str] = []
passes: list[str] = []


def check(name: str, condition: bool, detail: str) -> None:
    (passes if condition else failures).append(f"{name}: {detail}")


apps = json.loads((ROOT / "apps/package.json").read_text())
pyproject = tomllib.loads((ROOT / "server/pyproject.toml").read_text())
router = (ROOT / "server/app/agents/router.py").read_text()
main = (ROOT / "server/app/main.py").read_text()
termux_run = (ROOT / "termux/run-cathedral.sh").read_text()
telemetry = json.loads((ROOT / "analytics/event-catalog.json").read_text())
workflow = (ROOT / ".github/workflows/forge-ci.yml").read_text()

check("pass01-npm-only", apps.get("packageManager") == "npm@12.0.2", "npm is the declared JS package manager")
check("pass02-node-lts", ">=24.18 <25" in apps.get("engines", {}).get("node", ""), "Node 24 LTS is pinned for the tablet lane")
check("pass03-single-python", "fastapi[standard]" in " ".join(pyproject["project"]["dependencies"]), "FastAPI is the primary Python plane")
check("pass04-flask-mounted", 'app.mount("/compat", WSGIMiddleware(compat_app))' in main, "Flask is mounted, not separately served")
check("pass05-typed-ollama", "AgentDecision.model_json_schema()" in router and '"temperature": 0' in router, "Ollama output is schema constrained")
check("pass06-no-node-backend", not (ROOT / "apps/server.js").exists() and not (ROOT / "apps/server.ts").exists(), "no Node production backend exists")
check("pass07-loopback", "--host 127.0.0.1" in termux_run and "0.0.0.0" not in termux_run, "Termux control plane binds loopback")
check("pass08-telemetry-privacy", "prompt_text" in telemetry["forbidden_properties"] and "filesystem_path" in telemetry["forbidden_properties"], "analytics forbids prompt/path payloads")
check("pass09-copilot-policy", (ROOT / ".github/copilot-instructions.md").is_file() and (ROOT / "AGENTS.md").is_file(), "repository and agent instructions are present")
check("pass10-ci-contract", "architecture_sanity.py" in workflow and "node-version: '24'" in workflow, "CI executes the hard architecture gate on Node 24")

for item in passes:
    print("PASS", item)
for item in failures:
    print("FAIL", item, file=sys.stderr)

if failures:
    raise SystemExit(1)
print(f"GREEN {len(passes)}/10 architecture passes")
