# Samsung + private F-Droid local install lane

Status: private-development distribution only.

## What is already green

- Godot 4.7.2 Android debug export.
- arm64-v8a only.
- Android target SDK 36.
- Android min SDK 24.
- APK signature verification.
- 16 KiB ZIP alignment verification.
- Loopback-first local control-plane design.

## Samsung Android 16 install gate

For a normal local APK install, Developer options are not required.

On current Samsung Galaxy software, Auto Blocker can prevent apps from outside
Galaxy Store or Google Play from installing. For a trusted development APK:

1. Open Settings > Security and privacy > Auto Blocker.
2. Temporarily turn Auto Blocker off for the install if it blocks the APK.
3. Open Settings and search for "Install unknown apps".
4. Allow only the source that will perform this install, preferably F-Droid,
   Files, or Termux rather than enabling every source.
5. Install the APK.
6. Turn Auto Blocker back on when the development install is complete.

Developer options + USB debugging are only required for the ADB lane. They are
not required when tapping the APK and using Android's package installer.

ADB development install example:

```bash
adb devices -l
adb install -r video-forge-cathedral-debug.apk
```

If the installed package was signed with a different key, Android will reject an
in-place update. Uninstalling would remove the app's private data. The preferred
fix is to use one stable development signing key for every local build.

## Stable development signing

The GitHub Android workflow accepts an optional persistent development keystore
through repository secrets:

- `VIDEO_FORGE_ANDROID_KEYSTORE_B64`
- `VIDEO_FORGE_ANDROID_KEYSTORE_ALIAS`
- `VIDEO_FORGE_ANDROID_KEYSTORE_PASSWORD`

When all three exist, CI uses that stable key and records `stable-secret` in
`signing-mode.txt`. When they are absent, PR builds remain usable but are signed
with an ephemeral CI key and record `ephemeral-ci`.

Never commit a keystore or its password to Git.

## Termux local installer handoff

After downloading the APK to the tablet:

```bash
chmod +x termux/install-local-apk.sh
termux/install-local-apk.sh /absolute/path/to/video-forge-cathedral-debug.apk
```

The script hashes the APK, opens Android's per-source unknown-app settings for
Termux, and hands the APK to the system package installer. It does not bypass
Samsung or Android security controls.

## Private F-Droid lane

The Android workflow also creates `build/fdroid-stage/` containing:

```text
repo/art.eggiebagelface.videoforge.dev_4.apk
metadata/art.eggiebagelface.videoforge.dev.yml
SHA256SUMS
README.txt
```

This is intentionally a staging bundle, not a signed F-Droid repository.

On a trusted Ubuntu host with `fdroidserver` installed:

```bash
mkdir -p video-forge-fdroid
cd video-forge-fdroid
fdroid init
cp -a /path/to/fdroid-stage/repo/. repo/
cp -a /path/to/fdroid-stage/metadata/. metadata/
fdroid update
```

Keep the F-Droid repository keystore persistent and private. Publish the
resulting `repo/` directory over HTTPS, add that repository URL to the F-Droid
client on the Samsung tablet, and grant F-Droid permission under Install unknown
apps when Android asks.

A changing repository-signing key breaks repository trust. A changing APK
signing key breaks Android in-place updates. Treat both keys as durable identity.

## Official F-Droid status

Do not submit this fork to the official F-Droid repository yet.

The inherited repository currently lacks a project LICENSE file. Official
F-Droid requires FLOSS source and asset licensing and reviews the build chain.
The clean-room app lane must first receive an explicit compatible license and
all redistributed assets/dependencies must have recorded licenses.

The official-public lane is therefore:

```text
private Samsung smoke test
  -> stable app signing
  -> private F-Droid repo
  -> explicit clean-room FLOSS license
  -> asset/dependency license audit
  -> reproducible-source build review
  -> official F-Droid submission candidate
```
