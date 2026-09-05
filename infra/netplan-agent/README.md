# KAI 9000 Netplan Agent Lane

A guarded Ubuntu/Netplan automation lane for OpenAI-assisted network changes.

## Doctrine

The model **does not edit `/etc/netplan` and does not receive a root shell**.

```text
OpenAI agent
    |
    | typed JSON intent only
    v
Python policy broker
    |
    +--> inspect current Netplan state
    +--> validate interface + addresses + DNS + routes
    +--> render deterministic candidate
    +--> netplan generate / transactional stage
    |
    v
Operator approval boundary
    |
    +--> Netplan Try(timeout)
    +--> Apply on explicit approval
    +--> Cancel / timeout rollback otherwise
```

## Why this is the sane path

Netplan already provides a transactional configuration API over D-Bus. A temporary configuration object can be created from the current state, modified, tried with a timeout, applied, or cancelled. Use that transaction boundary instead of letting an AI overwrite YAML directly.

Persistent Netplan YAML under `/etc/netplan` must remain root-owned and mode `0600`.

## Agent capability boundary

Allowed agent operations:

- inspect merged Netplan state;
- propose a typed network intent;
- validate a proposal;
- request creation of a temporary candidate transaction;
- explain the expected connectivity impact.

Forbidden agent operations:

- arbitrary shell commands;
- arbitrary YAML payloads;
- direct writes to `/etc/netplan`;
- unconditional `netplan apply`;
- disabling all default routes;
- deleting the currently active management interface;
- changing firewall, DNS, VPN, or routing state outside the declared Netplan intent;
- confirming its own high-impact change.

## Intent schema

`schemas/netplan-intent.schema.json` is the machine contract. Keep the agent output structured and small. The first implementation supports one interface at a time and deliberately excludes bridges, bonds, VLANs, Wi-Fi secrets, tunnels, SR-IOV and Open vSwitch.

## Recommended execution flow

1. `python3 scripts/netplan_agent_sanity.py`
2. agent produces a JSON intent matching the schema;
3. deterministic Python policy validates the intent;
4. operator stages the candidate through the Netplan D-Bus configuration API;
5. operator invokes `Try()` with a short rollback timeout;
6. connectivity checks run from a non-agent process;
7. operator explicitly approves `Apply()` or allows timeout / invokes `Cancel()`.

## Connectivity gates

Before approval, require all configured gates that matter for the host, for example:

- management interface remains UP;
- default route exists when one existed before;
- configured DNS resolver responds;
- local KAI health endpoint responds;
- optional private LAN gateway responds;
- optional external HTTPS probe succeeds.

Never make a public Internet probe the sole success criterion.

## Ubuntu server default

For a headless Ubuntu host, prefer `networkd` unless the machine already has a deliberate NetworkManager policy. Do not silently switch renderers as part of an unrelated agent request.

## Android boundary

This lane is for Ubuntu/headless infrastructure. It does not run inside the Samsung Google Play APK and does not mutate Android networking.
