# Video Forge Plugin Experience Brief

Status: design only, not yet packaged or submitted

## Primary audience and recurring job

Creators running Video Forge on a local Android/Termux or workstation runtime who need to turn an MP4 into a resumable frame-by-frame AI mutation job, inspect progress, repair selected frames, preview the result, and export a final remuxed video without losing work when removable cache storage or an AI provider drops out.

## Product promise

Video Forge coordinates a deterministic FFmpeg pipeline around non-deterministic image generation: inspect media, stage a safe cache job, generate frames through a configured provider, validate results, preview progress, resume failures, and remux a finished video.

The Plugin does not promise that an AI provider will preserve perfect temporal consistency, that Android can physically unmount every removable volume, or that unavailable external providers can be invoked without their own configuration.

## Public Skill set

### 1. `forge-video-job`

Trigger: user wants to create, inspect, start, pause, resume, or diagnose a Video Forge render job.

Finished result: a validated job plan/state with deterministic FFmpeg stages and provider-neutral AI frame processing.

Includes:

- probe source media
- select CFR/VFR working mode
- create job manifest
- start/pause/resume/cancel generation
- inspect frame/job failures
- preserve resumability

### 2. `repair-video-frames`

Trigger: user wants to regenerate or inspect one frame/range/scene without restarting the whole video.

Finished result: selected frame tasks are safely regenerated and revalidated while completed unaffected frames remain intact.

Includes:

- frame-range selection
- scene/reference context
- prompt/seed/provider override
- before/after validation
- mark frame locked or accepted

### 3. `finalize-video-render`

Trigger: user wants a preview or final video assembled from accepted generated frames.

Finished result: preview or final FFmpeg output with source audio/metadata handling and explicit export/upload state.

Includes:

- preview build/status
- final remux/transcode
- duration/audio sanity checks
- upload/export handoff

## Internal-only capabilities

Do not advertise these as standalone public Skills:

- raw recursive filesystem deletion
- arbitrary shell execution
- arbitrary FFmpeg command execution from untrusted text
- secret/token management
- physical block-device mount/unmount commands
- provider-specific credential handling
- unrestricted Google Drive traversal

These are implementation details or sensitive boundaries.

## External app dependencies

### Google Drive

Optional for the core local renderer; required when the user wants Drive ingest, Drive checkpoints, or final Drive upload.

### GitHub

Development/repository dependency, not a required runtime dependency for normal video jobs.

### AI image provider

At least one configured provider is required for actual generated-frame mutation. The provider interface is vendor-neutral.

## Host-workspace capability profile

| Capability | Disposition | Purpose |
|---|---|---|
| read | preferred | inspect manifests, config, logs, frame metadata |
| list | preferred | inspect job/cache layout |
| search | preferred | discover project files/workflows |
| grep | preferred | find symbols/errors/settings |
| write | mutation | create job/config/generated artifacts |
| patch | mutation | focused code/config changes |
| shell | mutation | FFmpeg/ffprobe/tests/git when authorized |
| python | preferred | deterministic validation, metadata, hashes, job tooling |

`host-workspace-operator` should be included when the Plugin is packaged.

`sandbox-python-executor` should be included because deterministic frame/job validation, manifest transforms, archive inspection, hashing, and package checks materially improve correctness.

## Mutation boundary

Normal job actions that the user explicitly requests may mutate job state and cache artifacts.

The following actions require a clear explicit instruction in the current task:

- delete cached jobs or frames
- clean expired cache immediately
- overwrite an existing final render
- alter source media
- change provider credentials/configuration
- modify repository files
- run a physical mount/unmount/eject operation
- upload final media to a remote destination

Discovery and diagnosis should remain read-only until mutation is necessary.

## Invocation notes

Suitable for implicit discovery:

- inspect a Video Forge job
- explain a failed FFmpeg stage
- plan a frame repair
- explain cache state

Prefer explicit invocation/confirmation boundary for:

- cache deletion
- repository edits
- overwriting render outputs
- upload/publish operations
- mount/eject operations

## Starter prompt directions

1. "Turn this Drive MP4 into a 30 fps Video Forge job, use my USB cache, and show me the preview as frames finish."
2. "Frames 840 through 910 drifted off-model. Regenerate only that scene using the locked character reference and keep the rest of the render."
3. "The generation is complete. Sanity-check the frames and audio, remux the final MP4, then prepare it for Drive upload."

## Discovery test brief

### Direct prompts

- "Use Video Forge to demux this MP4 and generate the frames."
- "Resume my paused Video Forge job."
- "Remux these accepted frames back into the source audio."

### Indirect prompts

- "My AI video stopped after the USB drive disconnected. Can we continue where it left off?"
- "Only twenty frames look wrong. I do not want to rerender the whole movie."
- "I want to watch a low-res preview while the image model is still generating frames."

### Negative prompts

The Plugin should not implicitly claim ownership of:

- general video editing unrelated to the Video Forge workflow
- arbitrary disk cleanup
- unrestricted cloud file management
- generic image generation with no video/frame workflow
- package publishing or social-media posting

## Visual identity idea

A film-frame rectangle passing through a small forge gate and emerging as a sequence of clean frame tiles. Avoid generic sparkle/brain/robot iconography.

## Current blockers before Plugin packaging

1. Verify the target repository's software licensing/provenance before treating inherited CMS code as redistributable product code.
2. Replace or deliberately modernize the legacy Vite/Vue dependency set.
3. Implement and test the runtime workflow before compiling repository behavior into Skills.
4. Verify current official OpenAI Plugin/Skill manifest contracts immediately before creating public configuration.
5. Add repository-native tests and deterministic package validation before any submission-readiness claim.
