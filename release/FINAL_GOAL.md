# Luhm OS final goal

Product: **Luhm OS**  
Working title / codename: **KAI 9000**  
Android package: `art.eggiebagelface.videoforge.dev`

## Final release lane

```text
luhm-os-ultima source
        |
        |  committed apps/package-lock.json
        |  pre-Ultima source gate
        v
manual luhm-os-ultima-release
        |
        | exact authorization input: CAST ULTIMA
        | reproducible npm ci + Vue build
        | Godot/Gradle Android candidate build
        v
luhm-os-apk-candidate
        |
        | source run ID + exact source SHA
        v
manual luhm-os-fdroid-private-proxy
        |
        | persistent Android application signing identity
        | APK certificate SHA-256 pin
        | persistent F-Droid repository signing identity
        | fdroid update + signed index gate
        v
private static HTTPS /fdroid/repo/
        |
        v
F-Droid client import
```

## Package authority

- `dpkg` is the underlying Debian package layer.
- `apt/pkg` owns system packages.
- `pip` owns Python packages inside isolated virtual environments.
- Node.js is the JavaScript runtime.
- **npm is boss** for the Vue/Vite workspace and committed lockfile.
- FastAPI is the Python 3 production control plane; Flask is compatibility/debug only.
- Gradle and Godot own Android build glue.
- Termux and Termux:X11 are development lanes.
- Docker is workstation/cloud parity, not an Android runtime requirement.

## Rooted Samsung lane

The rooted Samsung development target keeps root outside the WebView/model authority. The APK must not expose a generic `su` relay. Privileged operations remain behind a typed, allowlisted broker. This release lane never disables SELinux or claims rooted Samsung hardware preserves Knox-backed features.

## Gates still requiring operator material

1. Generate `apps/package-lock.json` on a networked Node 24 / npm 12.0.2 environment using `scripts/luhm_generate_lockfile.sh`, review it, and commit it.
2. Configure the persistent Android application signing identity in the private GitHub secret boundary.
3. Configure the persistent F-Droid repository signing identity in the private GitHub secret boundary.
4. Configure the final private HTTPS repository host and deployment secrets.
5. Keep the repository certificate/fingerprint recorded out of band for F-Droid client verification.

No private signing key, signing password, API token, or repository Basic Auth password belongs in Git or Google Drive.

## Authority

Creating or editing this source does not authorize an APK build. The candidate workflow itself requires the exact input `CAST ULTIMA` and must be invoked manually. The private F-Droid proxy is a separate manual step after a successful candidate build.
