#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
wf=(ROOT/'.github/workflows/luhm-fdroid-private-proxy.yml').read_text()
sh=(ROOT/'scripts/luhm_fdroid_proxy.sh').read_text()
ng=(ROOT/'fdroid/proxy/nginx-private.conf.template').read_text()

checks=[
 ('manual-only','workflow_dispatch:' in wf and '\n  push:' not in wf and '\n  pull_request:' not in wf),
 ('artifact-upstream','/actions/runs/${SOURCE_RUN_ID}/artifacts' in sh),
 ('persistent-app-signer','LUHM_APP_CERT_SHA256' in sh and 'Persistent APK signer mismatch' in sh),
 ('persistent-repo-signer','LUHM_FDROID_KEYSTORE_B64' in sh and 'repo_keyalias' in sh),
 ('apk-signer-pin','AllowedAPKSigningKeys' in sh),
 ('fdroid-update','fdroid update --verbose' in sh),
 ('signed-index-gate','index-v2.json' in sh and 'entry.jar' in sh),
 ('https-only','[[ "$REPO_URL" == https://* ]]' in sh),
 ('private-basic-auth','auth_basic' in ng),
 ('static-deploy','rsync -az --delete' in sh),
 ('no-apk-build','--export-debug' not in sh+wf and '--export-release' not in sh+wf and 'gradle ' not in sh+wf),
 ('no-pages','pages' not in wf.lower()),
]
bad=[n for n,ok in checks if not ok]
for n,ok in checks: print(('PASS' if ok else 'FAIL'),n)
print(f'LUHM_FDROID_PROXY_SANITY {len(checks)-len(bad)}/{len(checks)}')
raise SystemExit(1 if bad else 0)
