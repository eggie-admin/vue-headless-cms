---
applyTo: "termux/**/*.sh"
---
Scripts must be Android/Termux-safe, loopback-first, idempotent where practical, and fail closed. Never hard-code removable-storage destructive paths. Do not expose Ollama, Flask, FastAPI, Vite, or VNC on `0.0.0.0` by default. Prefer `nodejs-lts`, npm, Python, FFmpeg, Git, and existing Ollama. Do not assume root.
