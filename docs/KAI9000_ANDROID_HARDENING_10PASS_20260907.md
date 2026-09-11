# KAI 9000 Android 10-Pass Hardening

Date: 2026-09-07
Lane: KAI 9000 / LuHm OS private Android testing

This document records the security invariants applied to the Samsung Android APK donor used by `eggie-admin/hydra-shell-android`.

1. **Component exposure**: app widget receiver is not exported. Custom widget actions must remain app-owned explicit PendingIntents.
2. **Termux command boundary**: only fixed verbs are permitted (`start`, `stop`, `benchmark`); no model-authored or caller-supplied shell command/path is accepted.
3. **Network boundary**: cleartext is denied globally and allowed only for loopback addresses required by the local control plane.
4. **WebView origin boundary**: packaged CMS uses `https://appassets.androidplatform.net`; file/content access and third-party cookies remain disabled; WebMessage listener accepts the packaged origin and main frame only.
5. **Navigation boundary**: non-appasset navigations leave the WebView and are delegated to Android rather than executing inside the privileged cockpit.
6. **Build provenance**: consuming repository must pin this donor by full commit SHA and verify downloaded Godot/Gradle archives by SHA-256.
7. **Signing separation**: debug signing is ephemeral testing identity only; release signing material is never committed and must use a separate reviewed release lane.
8. **Secret isolation**: API keys, tokens, credentials, keystores, and provider credential files are prohibited from source and APK assets.
9. **Artifact evidence**: APK promotion requires package identity, signature verification, SHA-256, ARM64 presence, bundled CMS evidence, and 16 KiB alignment checks.
10. **Fail-closed promotion**: testing must never auto-promote to release; production requires explicit signing, device validation, and reviewed promotion.

## Accepted testing constraint

The packaged CMS currently calls the loopback HTTP control plane from an HTTPS appassets origin, so WebView mixed-content compatibility remains necessary in the testing lane. This is constrained by the Network Security Configuration to loopback only. The long-term release target is to replace browser-direct HTTP with a typed native bridge or localhost TLS, allowing `MIXED_CONTENT_NEVER_ALLOW`.
