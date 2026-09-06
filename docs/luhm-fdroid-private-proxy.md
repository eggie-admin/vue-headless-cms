# Luhm OS private F-Droid proxy

Luhm OS keeps **KAI 9000** as the working title. The Android package ID remains
`art.eggiebagelface.videoforge.dev`.

This lane turns a prebuilt APK from a selected GitHub Actions run into a signed private
F-Droid binary repository. It does not compile the APK.

```text
GitHub APK artifact
      |
      v
persistent Android re-sign
      |
      v
fdroidserver update + repo signing
      |
      +--> GitHub Actions recovery artifact
      |
      +--> optional SSH/rsync HTTPS proxy
                   |
                   v
             F-Droid client
```

The client endpoint is a normal HTTPS URL ending in `/fdroid/repo/`. GitHub remains the
source/provenance/orchestration layer rather than pretending an Actions artifact URL is
an F-Droid repository.

## Required signing secrets

Android app identity: `LUHM_APP_KEYSTORE_B64`, `LUHM_APP_KEYSTORE_PASSWORD`,
`LUHM_APP_KEY_ALIAS`, `LUHM_APP_KEY_PASSWORD`, `LUHM_APP_CERT_SHA256`.

F-Droid repo identity: `LUHM_FDROID_KEYSTORE_B64`,
`LUHM_FDROID_KEYSTORE_PASSWORD`, `LUHM_FDROID_KEY_ALIAS`,
`LUHM_FDROID_KEY_PASSWORD`, `LUHM_FDROID_KEY_DNAME`.

Optional static proxy deployment: `LUHM_FDROID_DEPLOY_HOST`,
`LUHM_FDROID_DEPLOY_USER`, `LUHM_FDROID_DEPLOY_PATH`,
`LUHM_FDROID_DEPLOY_SSH_KEY`, `LUHM_FDROID_DEPLOY_HOST_KEY`.

Private keys and passwords are never committed. The workflow fails closed when the APK
certificate does not match `LUHM_APP_CERT_SHA256`.

## Import

A successful run writes `import.json` with the repository fingerprint. Import using:

`https://HOST/fdroid/repo/?fingerprint=REPO_CERT_SHA256`

If the proxy uses HTTP Basic Auth, use a dedicated repository account when importing:

`https://USERNAME:PASSWORD@HOST/fdroid/repo/?fingerprint=REPO_CERT_SHA256`

Do not use GitHub credentials as repository credentials.
