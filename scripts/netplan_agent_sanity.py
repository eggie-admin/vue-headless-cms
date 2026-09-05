#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "netplan-intent.schema.json"
MANIFEST = ROOT / "manifests" / "netplan-agent.manifest.json"
EXAMPLE = ROOT / "infra" / "netplan-agent" / "example-intent.json"
IFACE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,32}$")


def fail(message: str) -> None:
    print(f"NETPLAN_AGENT_SANITY_FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"cannot load {path.relative_to(ROOT)}: {exc}")
    if not isinstance(data, dict):
        fail(f"{path.relative_to(ROOT)} must contain a JSON object")
    return data


def validate_intent(intent: dict) -> None:
    allowed_top = {
        "interface",
        "ipv4",
        "reason",
        "expected_management_path",
        "change_ticket",
    }
    extras = set(intent) - allowed_top
    if extras:
        fail(f"unexpected top-level fields: {sorted(extras)}")

    interface = intent.get("interface")
    if not isinstance(interface, str) or not IFACE_RE.fullmatch(interface):
        fail("invalid interface identifier")

    reason = intent.get("reason")
    if not isinstance(reason, str) or not (1 <= len(reason) <= 500):
        fail("reason must be 1..500 characters")

    ipv4 = intent.get("ipv4")
    if not isinstance(ipv4, dict):
        fail("ipv4 must be an object")

    allowed_ipv4 = {"mode", "addresses", "routes", "dns"}
    extras = set(ipv4) - allowed_ipv4
    if extras:
        fail(f"unexpected ipv4 fields: {sorted(extras)}")

    mode = ipv4.get("mode")
    if mode not in {"dhcp", "static"}:
        fail("ipv4.mode must be dhcp or static")

    addresses = ipv4.get("addresses", [])
    if not isinstance(addresses, list) or len(addresses) > 8:
        fail("ipv4.addresses must be an array with at most 8 entries")
    parsed_networks = []
    for value in addresses:
        try:
            parsed = ipaddress.ip_interface(value)
        except ValueError:
            fail(f"invalid IPv4 CIDR address: {value!r}")
        if parsed.version != 4:
            fail(f"non-IPv4 address rejected: {value!r}")
        parsed_networks.append(parsed.network)

    if mode == "static" and not addresses:
        fail("static mode requires at least one IPv4 address")
    if mode == "dhcp" and addresses:
        fail("dhcp mode may not also declare static addresses in v1")

    dns = ipv4.get("dns", [])
    if not isinstance(dns, list) or len(dns) > 6:
        fail("ipv4.dns must be an array with at most 6 entries")
    for value in dns:
        try:
            parsed = ipaddress.ip_address(value)
        except ValueError:
            fail(f"invalid DNS address: {value!r}")
        if parsed.version != 4:
            fail(f"non-IPv4 DNS rejected in v1: {value!r}")

    routes = ipv4.get("routes", [])
    if not isinstance(routes, list) or len(routes) > 16:
        fail("ipv4.routes must be an array with at most 16 entries")

    default_routes = 0
    for route in routes:
        if not isinstance(route, dict):
            fail("each route must be an object")
        if set(route) - {"to", "via", "metric"}:
            fail("route contains unsupported fields")
        if "to" not in route or "via" not in route:
            fail("route requires to and via")
        to_value = route["to"]
        if to_value == "default":
            default_routes += 1
        else:
            try:
                destination = ipaddress.ip_network(to_value, strict=False)
            except ValueError:
                fail(f"invalid route destination: {to_value!r}")
            if destination.version != 4:
                fail(f"non-IPv4 route rejected in v1: {to_value!r}")
        try:
            via = ipaddress.ip_address(route["via"])
        except ValueError:
            fail(f"invalid route gateway: {route['via']!r}")
        if via.version != 4:
            fail("IPv6 gateway rejected in v1")
        metric = route.get("metric")
        if metric is not None and (not isinstance(metric, int) or not 1 <= metric <= 65535):
            fail("route metric must be 1..65535")

    if default_routes > 1:
        fail("v1 allows at most one default route per intent")


def validate_contract() -> None:
    schema = load_json(SCHEMA)
    manifest = load_json(MANIFEST)

    if schema.get("type") != "object":
        fail("intent schema must define an object")

    boundary = manifest.get("privilege_boundary", {})
    required_false = (
        "agent_runs_as_root",
        "agent_can_write_etc_netplan",
        "agent_can_apply_network_changes",
    )
    for key in required_false:
        if boundary.get(key) is not False:
            fail(f"privilege boundary must keep {key}=false")
    if boundary.get("operator_approval_required") is not True:
        fail("operator approval must remain required")
    if boundary.get("rollback_required") is not True:
        fail("rollback must remain required")

    allowed_tools = set(manifest.get("allowed_agent_tools", []))
    forbidden_tools = set(manifest.get("forbidden_agent_tools", []))
    if "netplan_apply" in allowed_tools:
        fail("netplan_apply must never be an allowed agent tool")
    if "shell" not in forbidden_tools or "netplan_apply" not in forbidden_tools:
        fail("shell and netplan_apply must remain forbidden")

    transaction = manifest.get("transaction", {})
    timeout = transaction.get("try_timeout_seconds_default")
    if not isinstance(timeout, int) or not 10 <= timeout <= 120:
        fail("try timeout must stay within 10..120 seconds")
    if transaction.get("commit_actor") != "human operator":
        fail("human operator must remain the commit actor")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", type=Path, help="optional intent JSON to validate")
    args = parser.parse_args()

    validate_contract()
    validate_intent(load_json(EXAMPLE))

    if args.intent:
        validate_intent(load_json(args.intent.resolve()))
        print(f"intent={args.intent}")

    print("NETPLAN_AGENT_SANITY_GREEN")
    print(f"schema={SCHEMA.relative_to(ROOT)}")
    print(f"manifest={MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
