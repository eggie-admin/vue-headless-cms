---
applyTo: "server/**/*.py,scripts/**/*.py,tests/**/*.py"
---
Use Python as the single backend language. Keep the FastAPI process async-first. Do not create a second Flask server; mount compatibility WSGI apps through FastAPI. All agent/model outputs must be validated with Pydantic before policy evaluation. Model-declared risk is advisory only; deterministic Python policy is authoritative. Never build shell commands from untrusted text. Keep telemetry sanitized and optional.
