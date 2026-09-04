# Samsung SM-X400 Source Ingest

The `samsung-sm-x400-ai` branch owns the source-code ingest lane.

## Purpose

Build a deterministic, secret-aware corpus from the repository so local Ollama retrieval and Lum/OpenAI context assembly can cite exact source chunks without executing repository code.

## Commands

From the repository root:

```bash
python3 scripts/source_ingest.py --smoke
python3 scripts/source_ingest.py --root . --output state/source-ingest
```

Or through npm:

```bash
npm --prefix apps run source:ingest:smoke
npm --prefix apps run source:ingest
```

## Outputs

- `state/source-ingest/source-manifest.json`
- `state/source-ingest/source-chunks.jsonl`

Each chunk carries path, language, file SHA-256, chunk SHA-256, and line range.

## Safety boundary

The ingest pass is read-only. It does not execute source files, follow symlinks, ingest runtime state, or include common secret-bearing files. `.env`, credentials, passwords, tokens, key material, SQLite state, build outputs, logs, virtualenvs, `node_modules`, and private directories are excluded.

Models may consume retrieved chunks as context. They do not gain shell authority from ingest. Python remains the mutation/policy gate.

## CI

The `samsung-source-ingest` workflow runs the smoke test, builds the branch corpus, verifies the corpus digest against its manifest, and uploads a 14-day `samsung-sm-x400-source-ingest` artifact for inspection or downstream retrieval experiments.
