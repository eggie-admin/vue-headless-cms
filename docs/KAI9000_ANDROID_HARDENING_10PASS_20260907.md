# KAI 9000 Android 10-Pass Hardening

Date: 2026-09-07
Updated: 2026-09-15
Lane: KAI 9000 / LuHm OS private Android testing

This document records the security invariants applied to the Samsung Android APK donor used by `eggie-admin/hydra-shell-android` and inherited by the current standalone LuHm OS lane.

1. **Component exposure**: app widget receiver is not exported. Custom widget actions must remain app-owned explicit PendingIntents.
2. **Command boundary**: production LuHm OS has no Termux command dependency. Legacy widget/template lanes may expose only fixed audited verbs; no model-authored or caller-supplied shell command/path is accepted.
3. **Network boundary**: cleartext is denied globally; any retained loopback exception is not a license for WebView mixed-content traffic.
4. **WebView origin boundary**: packaged CMS uses `https://appassets.androidplatform.net`; file/content access and cookies remain disabled; `MIXED_CONTENT_NEVER_ALLOW` is required; WebMessage listener accepts the packaged origin and main frame only.
5. **Navigation boundary**: non-appasset navigations leave the WebView and are delegated to Android only for audited safe schemes rather than executing inside the privileged cockpit.
6. **Build provenance**: consuming repositories pin donor revisions and verify downloaded Godot/Gradle archives and committed package locks by cryptographic hash.
7. **Signing separation**: debug signing is ephemeral testing identity only; release signing material is never committed and must use a separate reviewed persistent release/upload signer.
8. **Secret isolation**: API keys, tokens, credentials, keystores, and provider credential files are prohibited from source and APK assets. Google automation should use short-lived federated credentials rather than service-account JSON keys.
9. **Artifact evidence**: APK/AAB promotion requires package identity, signature/signer continuity as applicable, SHA-256 evidence, ARM64 presence, bundled CMS evidence, and required Android alignment/packaging checks.
10. **Fail-closed promotion**: testing must never auto-promote to production; production requires explicit signing, device validation, reviewed promotion, and all current Crown Gate checks green.

## 2026-09-15 Crown Gate closure

The old mixed-content compatibility exception is no longer the active WebView design. The standalone Godot Android shell now uses the packaged appassets origin with `MIXED_CONTENT_NEVER_ALLOW`; production has no external Termux daemon requirement. The automated current-state gate is `scripts/luhmos_crown_10pass.py`, and the Play-first distribution contract is `release/crown-install-lane.json`.

Google Play internal testing is the preferred low-friction install/update surface. A GitHub APK handoff remains a fallback and must retain Android's stock installer confirmation. Device root and custom silent installation are not part of this lane.
