# KAI 9000 OSS Vendor Hardening

KAI uses a **default-deny** vendor policy.

## Android downstream

For the Samsung SM-X400 developer forge, the approved Android downstream is `termux/termux-packages` at the commit recorded in `manifests/oss-vendors.lock.json`.

This is deliberately preferred over adopting miscellaneous Python or Godot forks. The Termux recipes retain the original upstream source identity while applying Android/Termux-specific build configuration, patches and dependency choices.

### Python

- Upstream: `python/cpython`
- Android downstream: Termux `packages/python/build.sh`
- KAI version: Python 3.14.6
- Source archive SHA-256 is locked in the vendor manifest.

### Godot

- Upstream: `godotengine/godot`
- Android downstream: Termux `x11-packages/godot/build.sh`
- KAI version: Godot 4.7.2
- Source archive SHA-256 is locked in the vendor manifest.

The Termux Godot recipe is the approved **Android patch/build layer**. It is not a separate KAI engine fork and does not change project format ownership.

## Python APK packaging

`kivy/python-for-android` is approved as a build tool only. It is not the KAI runtime authority. Its release and commit are locked in the vendor manifest and the Python build requirements retain an exact version pin.

## Fork admission gate

A new fork is rejected unless all of the following are true:

1. The upstream project cannot satisfy the required Android capability.
2. The fork has a clearly documented delta from upstream.
3. The fork is actively maintained and not archived.
4. License and provenance are known.
5. A specific immutable commit is selected.
6. CI proves the required KAI use case.
7. The fork does not introduce binary blobs or executable downloads without verified hashes.
8. The fork can be removed without changing KAI data formats or public API contracts.

A high star count is not a security property.

## GitHub Actions

All external GitHub Actions must:

- come from an approved repository;
- use a full 40-character commit SHA;
- appear in `manifests/oss-vendors.lock.json`;
- run with minimum workflow permissions.

Mutable references such as `@main`, `@master`, `@develop`, `@v4` or `@v5` are not accepted by the vendor sanity gate.

## Verification

Run:

```bash
python3 scripts/vendor_sanity.py
```

Expected:

```text
OSS_VENDOR_SANITY_GREEN
```

The check is deterministic and does not contact GitHub. Updating a vendor requires a reviewed manifest change plus the corresponding immutable reference change.

## Rejected examples

The lock manifest records rejected candidates so that misleading names or abandoned forks are not rediscovered and accidentally promoted later.
