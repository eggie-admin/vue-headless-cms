#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ID='art.eggiebagelface.videoforge.dev'
: "${SOURCE_RUN_ID:?}"
: "${SOURCE_ARTIFACT_NAME:?}"
: "${REPO_URL:?}"
: "${GH_TOKEN:?}"

[[ "$REPO_URL" == https://* ]] || { echo 'repo_url must use HTTPS' >&2; exit 20; }
[[ "$REPO_URL" == */fdroid/repo/ || "$REPO_URL" == */fdroid/repo ]] || {
  echo 'repo_url must end in /fdroid/repo/' >&2; exit 21;
}

signing_required=(
  LUHM_APP_KEYSTORE_B64 LUHM_APP_KEYSTORE_PASSWORD LUHM_APP_KEY_ALIAS
  LUHM_APP_KEY_PASSWORD LUHM_APP_CERT_SHA256
  LUHM_FDROID_KEYSTORE_B64 LUHM_FDROID_KEYSTORE_PASSWORD
  LUHM_FDROID_KEY_ALIAS LUHM_FDROID_KEY_PASSWORD LUHM_FDROID_KEY_DNAME
)
for name in "${signing_required[@]}"; do
  [[ -n "${!name:-}" ]] || { echo "Missing required signing secret: $name" >&2; exit 22; }
done

APKSIGNER="$(command -v apksigner || true)"
ZIPALIGN="$(command -v zipalign || true)"
AAPT="$(command -v aapt || true)"
if [[ -n "${ANDROID_HOME:-}" ]]; then
  [[ -n "$APKSIGNER" ]] || APKSIGNER="$(find "$ANDROID_HOME/build-tools" -type f -name apksigner 2>/dev/null | sort -V | tail -1)"
  [[ -n "$ZIPALIGN" ]] || ZIPALIGN="$(find "$ANDROID_HOME/build-tools" -type f -name zipalign 2>/dev/null | sort -V | tail -1)"
  [[ -n "$AAPT" ]] || AAPT="$(find "$ANDROID_HOME/build-tools" -type f -name aapt 2>/dev/null | sort -V | tail -1)"
fi
test -x "$APKSIGNER"; test -x "$ZIPALIGN"; test -x "$AAPT"

rm -rf work
mkdir -p work/source work/keys work/fdroid/repo work/fdroid/metadata work/provenance
chmod 700 work/keys
umask 077

api="https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/runs/${SOURCE_RUN_ID}/artifacts?per_page=100"
curl --fail --silent --show-error \
  -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' \
  "$api" > work/provenance/artifacts.json
artifact_id="$(jq -r --arg n "$SOURCE_ARTIFACT_NAME" \
  '.artifacts[] | select(.name==$n and .expired==false) | .id' \
  work/provenance/artifacts.json | head -1)"
[[ "$artifact_id" =~ ^[0-9]+$ ]] || { echo 'Artifact missing or expired' >&2; exit 23; }

curl --fail --location --silent --show-error \
  -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' \
  "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/artifacts/${artifact_id}/zip" \
  -o work/source-artifact.zip
unzip -q work/source-artifact.zip -d work/source
mapfile -t apks < <(find work/source -type f -name '*.apk' -print)
[[ "${#apks[@]}" -eq 1 ]] || { echo "Expected one APK, found ${#apks[@]}" >&2; exit 24; }
SOURCE_APK="${apks[0]}"
sha256sum "$SOURCE_APK" > work/provenance/source-apk.sha256

"$AAPT" dump badging "$SOURCE_APK" > work/provenance/source-badging.txt
pkg="$("$AAPT" dump badging "$SOURCE_APK" | sed -n "s/^package: name='\([^']*\)'.*/\1/p" | head -1)"
vcode="$("$AAPT" dump badging "$SOURCE_APK" | sed -n "s/^package:.*versionCode='\([^']*\)'.*/\1/p" | head -1)"
vname="$("$AAPT" dump badging "$SOURCE_APK" | sed -n "s/^package:.*versionName='\([^']*\)'.*/\1/p" | head -1)"
[[ "$pkg" == "$PACKAGE_ID" && "$vcode" =~ ^[0-9]+$ && -n "$vname" ]] || exit 25
export SOURCE_VERSION_CODE="$vcode" SOURCE_VERSION_NAME="$vname" PACKAGE_ID

printf '%s' "$LUHM_APP_KEYSTORE_B64" | base64 --decode > work/keys/app.keystore
chmod 600 work/keys/app.keystore
"$ZIPALIGN" -f -p 4 "$SOURCE_APK" work/aligned.apk
SIGNED_APK="work/fdroid/repo/${PACKAGE_ID}_${vcode}.apk"
"$APKSIGNER" sign \
  --ks work/keys/app.keystore --ks-key-alias "$LUHM_APP_KEY_ALIAS" \
  --ks-pass env:LUHM_APP_KEYSTORE_PASSWORD --key-pass env:LUHM_APP_KEY_PASSWORD \
  --out "$SIGNED_APK" work/aligned.apk
"$APKSIGNER" verify --verbose --print-certs "$SIGNED_APK" > work/provenance/app-signature.txt
actual="$("$APKSIGNER" verify --print-certs "$SIGNED_APK" |
  sed -n 's/^Signer #1 certificate SHA-256 digest: //p' | head -1 |
  tr -d ':' | tr '[:upper:]' '[:lower:]')"
expected="$(printf '%s' "$LUHM_APP_CERT_SHA256" | tr -d ':' | tr '[:upper:]' '[:lower:]')"
[[ "$actual" =~ ^[0-9a-f]{64}$ && "$actual" == "$expected" ]] || {
  echo 'Persistent APK signer mismatch' >&2; exit 26;
}
export APP_CERT_SHA256="$actual"
sha256sum "$SIGNED_APK" > work/provenance/signed-apk.sha256

printf '%s' "$LUHM_FDROID_KEYSTORE_B64" | base64 --decode > work/keys/fdroid-repo.keystore
chmod 600 work/keys/fdroid-repo.keystore
cp fdroid/metadata/art.eggiebagelface.videoforge.dev.yml \
  work/fdroid/metadata/art.eggiebagelface.videoforge.dev.yml

python3 - <<'PY'
import os, re
from pathlib import Path
p=Path('work/fdroid/metadata/art.eggiebagelface.videoforge.dev.yml')
s=p.read_text()
s=re.sub(r'(?m)^CurrentVersion:.*$', 'CurrentVersion: '+os.environ['SOURCE_VERSION_NAME'], s)
s=re.sub(r'(?m)^CurrentVersionCode:.*$', 'CurrentVersionCode: '+os.environ['SOURCE_VERSION_CODE'], s)
s=re.sub(r'(?ms)^AllowedAPKSigningKeys:\n(?:  - .*\n)+', '', s)
s += '\nAllowedAPKSigningKeys:\n  - '+os.environ['APP_CERT_SHA256']+'\n'
p.write_text(s)
PY

export FDROID_KEYSTORE="$(realpath work/keys/fdroid-repo.keystore)"
python3 - <<'PY'
import json, os
from pathlib import Path
cfg={
 'repo_url':os.environ['REPO_URL'],
 'repo_name':'Luhm OS Private Dev Repository',
 'repo_description':'Private binary repository for Luhm OS (working title KAI 9000).',
 'archive_older':0,
 'keystore':os.environ['FDROID_KEYSTORE'],
 'repo_keyalias':os.environ['LUHM_FDROID_KEY_ALIAS'],
 'keystorepass':os.environ['LUHM_FDROID_KEYSTORE_PASSWORD'],
 'keypass':os.environ['LUHM_FDROID_KEY_PASSWORD'],
 'keydname':os.environ['LUHM_FDROID_KEY_DNAME'],
}
with Path('work/fdroid/config.yml').open('w') as f:
    for k,v in cfg.items(): f.write(f'{k}: {json.dumps(v)}\n')
PY
chmod 600 work/fdroid/config.yml

(
  cd work/fdroid
  fdroid update --verbose
  test -s repo/index-v2.json || test -s repo/index-v1.jar || test -s repo/entry.jar
  keytool -exportcert -keystore ../keys/fdroid-repo.keystore \
    -storepass "$LUHM_FDROID_KEYSTORE_PASSWORD" -alias "$LUHM_FDROID_KEY_ALIAS" 2>/dev/null |
    sha256sum | awk '{print toupper($1)}' > repo-fingerprint.txt
)
fingerprint="$(cat work/fdroid/repo-fingerprint.txt)"
[[ "$fingerprint" =~ ^[0-9A-F]{64}$ ]] || exit 27
export REPO_FINGERPRINT="$fingerprint"

python3 - <<'PY'
import json, os
from pathlib import Path
base=os.environ['REPO_URL'].rstrip('/')
fp=os.environ['REPO_FINGERPRINT']
Path('work/fdroid/import.json').write_text(json.dumps({
 'name':'Luhm OS Private Dev Repository',
 'workingTitle':'KAI 9000',
 'packageId':os.environ['PACKAGE_ID'],
 'versionName':os.environ['SOURCE_VERSION_NAME'],
 'versionCode':int(os.environ['SOURCE_VERSION_CODE']),
 'url':base+'/',
 'fingerprint':fp,
 'importUrl':base+'/?fingerprint='+fp,
 'privateAuth':'Optional HTTP Basic Auth; credentials are added only on the Android client.'
},indent=2)+'\n')
PY

find work/fdroid/repo -type f -print0 | sort -z | xargs -0 sha256sum > work/fdroid/SHA256SUMS

if [[ "${PUBLISH:-false}" == 'true' ]]; then
  deploy_required=(LUHM_FDROID_DEPLOY_HOST LUHM_FDROID_DEPLOY_USER LUHM_FDROID_DEPLOY_PATH LUHM_FDROID_DEPLOY_SSH_KEY LUHM_FDROID_DEPLOY_HOST_KEY)
  for name in "${deploy_required[@]}"; do
    [[ -n "${!name:-}" ]] || { echo "Missing deploy secret: $name" >&2; exit 28; }
  done
  install -d -m 700 "$HOME/.ssh"
  printf '%s\n' "$LUHM_FDROID_DEPLOY_SSH_KEY" > "$HOME/.ssh/id_ed25519"
  printf '%s\n' "$LUHM_FDROID_DEPLOY_HOST_KEY" > "$HOME/.ssh/known_hosts"
  chmod 600 "$HOME/.ssh/id_ed25519" "$HOME/.ssh/known_hosts"
  remote="${LUHM_FDROID_DEPLOY_USER}@${LUHM_FDROID_DEPLOY_HOST}"
  root="${LUHM_FDROID_DEPLOY_PATH%/}"
  ssh -i "$HOME/.ssh/id_ed25519" "$remote" "mkdir -p '$root/repo' '$root/archive'"
  rsync -az --delete -e "ssh -i $HOME/.ssh/id_ed25519" work/fdroid/repo/ "$remote:$root/repo/"
  [[ ! -d work/fdroid/archive ]] || rsync -az --delete -e "ssh -i $HOME/.ssh/id_ed25519" work/fdroid/archive/ "$remote:$root/archive/"
fi

cat > work/provenance/summary.md <<EOF
## Luhm OS private F-Droid proxy

- Source run: ${SOURCE_RUN_ID}
- Source artifact: ${SOURCE_ARTIFACT_NAME}
- Package: ${PACKAGE_ID}
- Version: ${SOURCE_VERSION_NAME} (${SOURCE_VERSION_CODE})
- APK signer SHA-256: ${APP_CERT_SHA256}
- F-Droid repo fingerprint: ${REPO_FINGERPRINT}
- Repo URL: ${REPO_URL}
- Published: ${PUBLISH:-false}
- APK compile performed by this workflow: **NO**
EOF
