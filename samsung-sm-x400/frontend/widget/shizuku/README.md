# Shizuku privilege-broker lane

This is an **optional** Samsung SM-X400 frontend/widget capability. It is not part of the APK dependency graph and it does not make root a requirement.

## Preferred Secure Folder development mode

Use Shizuku in ADB / wireless-debugging mode on the stock Knox-capable target.

- Developer Options: enabled
- USB or Wireless debugging: operator controlled
- Shizuku: installed separately by the operator
- app authorization: explicit, per app
- no root requirement
- no Sui requirement
- no hidden-API bypass dependency by default

The application must detect whether Shizuku is available and authorized. Missing Shizuku is a capability downgrade, not a build failure.

## Rooted laboratory mode

A rooted Samsung may use Shizuku root mode or Sui, but that is a separate laboratory trust lane. Do not claim Secure Folder/Knox trust on a device whose Knox warranty state has been compromised.

Root is never auto-selected merely because `su` exists. Root-only actions require an explicit architecture and operator authorization gate.

## Stage 1 integration

The first integration stage is intentionally narrow:

1. detect whether the Shizuku manager/service is present
2. request the normal Shizuku user authorization flow
3. expose read-only device diagnostics through typed actions
4. fall back cleanly to ordinary Android/ADB behavior when unavailable

No arbitrary model-authored shell execution is allowed.

## Stage 2

Direct Shizuku API dependencies, package-manager mutations, cross-user operations, and root-only actions remain blocked until a concrete feature requires them and the Android permission boundary has been reviewed.

## Build commands

From `apps/`:

```bash
npm run shizuku:check
npm run candidate:build:shizuku
npm run wizard
```

`candidate:build:shizuku` means frontend candidate + widget bundle + Shizuku contract validation. It still does not embed the external Shizuku manager into the APK.
