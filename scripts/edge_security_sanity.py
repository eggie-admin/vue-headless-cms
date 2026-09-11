from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "infra/edge/edge-security.manifest.json"
OPENVPN = ROOT / "infra/openvpn/server.conf.template"
OPENSSL = ROOT / "infra/openssl/openssl.cnf"
CLOUDFLARE = ROOT / "infra/cloudflare/config.yml.template"

passes = 0


def check(condition: bool, message: str) -> None:
    global passes
    if not condition:
        raise SystemExit(f"EDGE_SECURITY_SANITY_FAIL: {message}")
    passes += 1


manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
openvpn = OPENVPN.read_text(encoding="utf-8")
openssl = OPENSSL.read_text(encoding="utf-8")
cloudflare = CLOUDFLARE.read_text(encoding="utf-8")

check(manifest["fqdn"]["apex"] == "eggiebagelface.art", "wrong apex FQDN")
check(manifest["ingress"]["public"] == "cloudflare_tunnel", "public ingress must be Cloudflare Tunnel")
check(manifest["ingress"]["origin_scheme"] == "https", "origin transport must be HTTPS")
check(manifest["ingress"]["no_public_origin_ports"] is True, "origin ports must not be public")
check(manifest["identity"]["human_edge"] == "cloudflare_access", "human edge must use Cloudflare Access")
check(manifest["identity"]["idp"] == "google_or_google_workspace", "Google identity sentry missing")
check(manifest["identity"]["google_iap_for_termux_origin"] is False, "do not double-proxy Termux through Google IAP")
check(manifest["identity"]["machine_auth"] == "cloudflare_access_service_token", "machine auth must use Access service tokens")
check(manifest["vpn"]["role"] == "break_glass_private_admin", "OpenVPN must not become app ingress")
check(manifest["vpn"]["force_cookie"] is True, "OpenVPN force-cookie required")
check(manifest["vpn"]["compression"] is False, "VPN compression must be disabled")
check(manifest["openssl"]["security_level"] == 2, "OpenSSL security level must be 2")
check("tls-crypt-v2" in openvpn and "force-cookie" in openvpn, "tls-crypt-v2 force-cookie missing")
check("allow-compression no" in openvpn, "OpenVPN compression hardening missing")
check("data-ciphers-fallback" not in "\n".join(line for line in openvpn.splitlines() if not line.lstrip().startswith("#")), "legacy cipher fallback enabled")
check("MinProtocol = TLSv1.2" in openssl and "@SECLEVEL=2" in openssl, "OpenSSL baseline missing")
check("https://127.0.0.1:8443" in cloudflare, "Tunnel origin must use HTTPS")
check(cloudflare.count("noTLSVerify: false") == 3, "origin certificate verification must remain enabled")
check("http_status:404" in cloudflare, "Tunnel needs fail-closed catch-all")

combined = "\n".join([MANIFEST.read_text(), openvpn, openssl, cloudflare])
for forbidden in ("sk-proj-", "cfast_", "BEGIN PRIVATE KEY", "BEGIN OPENSSH PRIVATE KEY"):
    check(forbidden not in combined, f"secret-like material found: {forbidden}")

print(f"EDGE_SECURITY_SANITY_GREEN passes={passes}")
