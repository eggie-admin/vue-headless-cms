# Video Forge Cathedral Interface v2

Status: implementation scaffold, not production-ready.

## Decision

Use separate execution planes with one product surface:

- **Godot 4.7.2**: fullscreen cage, 3D avatar, top-level embedded windows, animation and cutscene playback.
- **Vue 3.5 + Vite 8**: clean-room admin/CMS panels. The legacy CMS remains untouched until licensing/provenance is resolved.
- **jQuery UI 1.14.2**: compatibility-only draggable/resizable wrapper for selected Vue panel roots. It must not own application state or mutate Vue-managed descendants.
- **Tablet FastAPI**: local bridge to FFmpeg, USB cache, SQLite, Ollama, Godot, and outbound cloud synchronization.
- **FastAPI Cloud**: remote control API and shared state/event plane. Autoscaled replicas require Redis/Postgres for shared state instead of process memory.
- **Modal**: GPU jobs for image generation, LoRA/QLoRA tuning, adapter merge/export, and optional hosted tuned-model inference.
- **Vercel**: remote Vue preview/admin deployment and review surface, not the FFmpeg or GPU furnace.
- **GitHub**: source, schemas, CI, review and release metadata.

## Android-first topology

```text
Samsung tablet
  Godot cage + avatar stage
        |
        +-- local FastAPI bridge ---- FFmpeg / SQLite / USB-C cache
        |            |
        |            +------------- Ollama Lite
        |
        +-- Vue admin panel (standalone now; Android WebView v2 bridge later)
        |
        +-- outbound authenticated sync
                     |
                     v
               FastAPI Cloud
                 |       |
              Redis    Postgres
                 |
                 +---- OpenAI Lum (gpt-5.6-sol)
                 |
                 +---- Modal GPU jobs ---- Hugging Face TRL/PEFT

Vercel: remote Vue preview/admin mirror
GitHub: source + PR + CI
```

## Agent policy

`Lum Lite` is local and low-latency. Use it for typed local intents, UI navigation, simple cache/job status, and offline structured responses. Ollama supports structured outputs and streaming tool calls; model selection remains configurable and should be capability-checked with `ollama show` rather than hard-coded.

`Lum Cloud` uses the OpenAI Agents SDK with `gpt-5.6-sol` for complex reasoning and tool orchestration. GPT-5.6 Sol supports function calling and structured outputs but is not fine-tunable. Customize it with instructions, tools, skills, memory, evals and structured project state.

The router is local-first only when the local runtime is explicitly configured and the requested action is safe. Do not route destructive actions from natural-language heuristics.

## Hugging Face tuning lane

Tune only open/local models. Use TRL + PEFT LoRA/QLoRA on Modal. Persist checkpoints/adapters in a Modal Volume or a licensed Hugging Face repository. For tablet deployment, merge the adapter into the licensed base model, export/quantize to GGUF, then import into Ollama. Do not attempt to fine-tune GPT-5.6 Sol.

## Questforge-inspired play-state mutation

Borrow the state architecture, not the fantasy rules:

```text
projects/<slug>/
  project-state.json
  scene-state.json
  character-bible.json
  visual-bible.json
  checkpoints/
  cutscenes/
  sessions/
  events.jsonl
```

Canonical structured state wins over chat prose when they disagree. Create checkpoints before destructive media edits, irreversible scene branches, model replacement, or cache eviction of non-uploaded outputs.

## Godot cutscene contract

Godot `AnimationPlayer` stores/imports animation clips. `AnimationTree` owns advanced transition/blend playback. The cutscene director consumes validated JSON beats and dispatches only typed operations:

- `set_avatar_state`
- `play_animation`
- `set_camera`
- `speak_dialogue`
- `play_audio_cue`
- `emit_event`
- `wait_for`

Keep AI-generated prose out of direct node paths and arbitrary method calls.

## Window system

Godot is the top-level compositor. `Window` nodes are embedded in the main viewport so the app remains one fullscreen cage. Vue/jQuery panels are content surfaces, not the authoritative desktop manager.

Initial windows:

1. Video Forge queue
2. Video preview
3. Frame inspector
4. Prompt/scene studio
5. Character + visual bible
6. Lum agent console
7. Cutscene director
8. Model tuning
9. Cache/storage
10. System log/settings

## Cloud boundaries

FastAPI Cloud autoscaling/scale-to-zero is useful for the control plane, but shared WebSocket/job state must live in Redis/Postgres. Cloud instances cannot reach the tablet's localhost Ollama or removable USB media. The tablet initiates outbound sync.

Modal owns expensive GPU work. Modal Volumes persist shared model/checkpoint data but concurrent writers to the same file should be avoided.

Vercel owns the remote Vue surface and preview deployments. Do not run FFmpeg frame farms or model training there.

## Security

No API keys in Vue, Godot resources, Git history, prompts, or cutscene JSON.

Agent tools must be typed and bounded. Examples:

- `inspect_cache`
- `start_job`
- `pause_job`
- `regenerate_frame`
- `pin_job`
- `play_cutscene`
- `set_avatar_state`
- `finalize_video`

No general `run_shell(command)` or `delete(path)` tool.

Treat prompts, scene JSON, model output, imported media metadata, and remote job payloads as untrusted input.

## Milestone 1

Prove the shell before attaching expensive AI:

1. Godot cage boots fullscreen.
2. Embedded Godot tool windows move/resize.
3. Vue admin builds independently.
4. Local FastAPI `/api/health` and `/ws/events` work.
5. Fake render progress animates the avatar/UI.
6. Cutscene JSON validates and plays timed beats.
7. USB cache state remains local to tablet.
8. CI builds Vue and syntax-checks Python/JSON.

Then add Ollama, OpenAI, Modal image generation, Hugging Face tuning, and cloud synchronization one layer at a time.
