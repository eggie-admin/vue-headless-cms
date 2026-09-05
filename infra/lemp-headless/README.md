# KAI 9000 Headless LEMP Lane

This is infrastructure for a Linux host. It is **not** part of the Samsung APK and it is not a second AI control plane.

## Sanest split

```text
client / tunnel / LAN TLS
          |
        Nginx
     /     |      \
 static  FastAPI  PHP-FPM (optional compatibility only)
           |
        MariaDB
           |
        durable state

Ollama stays localhost-only and is reached by FastAPI, never exposed directly by Nginx.
```

## Roles

- **Linux**: stable headless host.
- **Nginx**: HTTP/TLS front door, static assets, reverse proxy, request limits.
- **MariaDB**: durable application state. Bind to loopback unless a dedicated private DB network is explicitly required.
- **PHP-FPM**: optional compatibility lane only. Do not make PHP the KAI control plane.
- **FastAPI**: canonical KAI application/API process.
- **Ollama**: localhost model runtime behind FastAPI.
- **Vue/Godot**: clients. They do not talk directly to MariaDB or Ollama.

## Default network boundary

Recommended headless default:

- Nginx: `127.0.0.1:8080` when fronted by a tunnel/local TLS gateway.
- FastAPI: `127.0.0.1:8000`.
- MariaDB: `127.0.0.1:3306`.
- Ollama: `127.0.0.1:11434`.
- PHP-FPM: Unix-domain socket.

Only Nginx is a candidate for exposure. Database, Ollama, FastAPI and PHP-FPM stay private.

## Install plane

On Ubuntu/Debian, keep packages boring and distro-managed:

```bash
sudo apt update
sudo apt install nginx mariadb-server

# Only if a PHP compatibility application actually exists:
sudo apt install php-fpm php-cli php-mysql
```

Do not install PHP merely because the acronym LEMP contains a P.

## Service management

Use the operating system supervisor (`systemd` on Ubuntu) for Nginx, MariaDB and FastAPI. Do not run production services from interactive shells or tmux.

Suggested process ownership:

- `/srv/kai9000/www` static built UI, root-owned, read-only to the web user.
- `/srv/kai9000/app` deployed Python application.
- `/etc/kai9000/kai9000.env` secrets/config, root-owned `0600`.
- `/var/lib/kai9000` mutable app state if filesystem state is required.
- MariaDB owns database files under its normal distro path.

## Proxy rules

Nginx should:

1. serve static UI directly;
2. proxy `/api/` to FastAPI;
3. preserve trusted forwarded host/protocol headers;
4. support WebSocket upgrade only on paths that need it;
5. disable proxy buffering on token/SSE streaming endpoints;
6. reject large request bodies by default and raise limits only on explicit upload routes;
7. never proxy a public `/ollama/` endpoint.

## Database rules

- one dedicated MariaDB user for KAI;
- no application use of MariaDB `root`;
- password comes from environment/secret storage, never Git;
- migrations are explicit and reviewed;
- regular logical backups plus tested restore procedure;
- keep remote DB access disabled unless there is a deliberate private-network design.

## PHP compatibility rules

If PHP is unnecessary, leave PHP-FPM uninstalled.

If needed:

- use the distro PHP-FPM package;
- communicate over its Unix socket;
- limit PHP execution to a dedicated `/compat` tree;
- never allow arbitrary uploaded files to become executable PHP;
- keep KAI orchestration in FastAPI/Python.

## Deployment sanity

```bash
nginx -t
systemctl is-active nginx
systemctl is-active mariadb
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8080/api/health
ss -lntp
```

Expected rule: MariaDB, FastAPI and Ollama must not be listening on a public wildcard address.

## Android boundary

The SM-X400 can be a developer/client device, but the Google Play APK does not embed this LEMP stack. The one-app Android lane talks to a local embedded runtime or an authenticated server API. LEMP remains server infrastructure.
