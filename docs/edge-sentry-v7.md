# Edge Sentry v7

Video Forge keeps three security planes separate.

## Public application plane

`api.eggiebagelface.art`, `cms.eggiebagelface.art`, and `forge.eggiebagelface.art` enter through Cloudflare Tunnel only. The origin exposes no public HTTP port. Cloudflare Access protects operator surfaces, Cloudflare handles edge DDoS/WAF policy, and cloudflared validates the local HTTPS origin certificate. Use Full (strict) at the zone edge.

## Google sentry

For the current Termux/Android origin, Google is an identity provider to Cloudflare Access. Use Google or Google Workspace OAuth/OIDC with PKCE enabled and explicit Access allow policies. Do not put Google IAP behind Cloudflare for this topology. IAP becomes appropriate only if the protected workload moves behind a Google Cloud service/load balancer that IAP natively supports.

Human users authenticate with Google identity and receive short-lived Access sessions. Automated systems use Cloudflare Access service tokens, never a human OAuth cookie. Provider API keys remain backend-only and are never returned to Vue, Godot, WebView, or APK code.

## Private admin plane

OpenVPN is break-glass private network access, not the public application ingress. The server belongs on a trusted Ubuntu/gateway host. Android/Termux may be a client. Use per-device certificates, CRL revocation, `tls-crypt-v2 ... force-cookie`, AEAD data ciphers, and no compression or legacy fallback. Restrict VPN routes/firewall rules to private administration targets only.

## Origin TLS

Use an HTTPS listener on loopback, recommended `127.0.0.1:8443`, with a certificate whose SANs cover the routed FQDNs. A private origin CA is acceptable when cloudflared is configured with its CA pool. Certificate verification stays enabled. OpenSSL baseline is TLS 1.2 minimum, TLS 1.3 preferred, security level 2.

## Secret doctrine

Credential values live only in protected environment/files or provider secret stores. Tokens travel in HTTPS headers, not query strings. Tunnel credentials, OAuth client secrets, OpenVPN private keys, CA private keys, Cloudflare service-token secrets, and OpenAI keys are never committed or embedded in the APK.
