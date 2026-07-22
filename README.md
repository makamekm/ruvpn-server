# RUPN Server

Self-hosted single-room RUPN server. One container runs and supervises one `olcrtc -mode srv` process and prints the JWT that RUPN clients import.

The image contains the current RUPN `olcrtc` server runtime with Telemost VP8 recovery fixes and is published for `linux/amd64` and `linux/arm64`.

## Requirements

- A Linux server with Docker and outbound internet access.
- A Telemost room. Create a meeting in Telemost and copy its invite URL.
- A RUPN client compatible with `telemost/vp8channel`.

No ports need to be published: the server establishes outbound connections to Telemost and the configured DNS resolver.

## Quick start

Paste the complete Telemost URL or only the numeric room id:

```bash
docker run -d \
  --name rupn-server \
  --restart unless-stopped \
  -e 'RUPN_TELEMOST_ROOM=https://telemost.yandex.ru/j/12345678901234' \
  -v rupn-server-state:/var/lib/rupn-server \
  makame/rupn-server:latest

docker logs -f rupn-server
```

Startup logs contain:

```text
RUPN server started
RUPN_CONNECTION_TYPE=telemost
RUPN_TELEMOST_ROOM_ID=12345678901234
RUPN_DEVICE_NAME=device-...
RUPN_CONNECT_JWT=eyJhbG...
```

Import `RUPN_CONNECT_JWT` into the RUPN client. The raw URI, which contains the private key, is not logged by default.

## Docker Compose

```bash
mkdir ruvpn-server && cd ruvpn-server
curl -fsSLO https://raw.githubusercontent.com/makamekm/ruvpn-server/main/docker-compose.yml
curl -fsSL https://raw.githubusercontent.com/makamekm/ruvpn-server/main/.env.example -o .env
```

Edit `.env` and set `RUPN_TELEMOST_ROOM` to your Telemost invite URL, then start:

```bash
docker compose up -d
docker compose logs -f rupn-server
```

Update later with:

```bash
docker compose pull
docker compose up -d
```

## JWT, key, and device identity

### Will a service restart create a new JWT?

Yes by default. Every container/service start generates a random 256-bit client key and a random device name, then prints a new `RUPN_CONNECT_JWT`. This happens even when the Docker state volume is preserved.

Re-import the newly printed `RUPN_CONNECT_JWT` into the mobile client after every `docker restart`, `docker compose up -d` recreate, host reboot, or service restart unless you pinned the credentials through environment variables.

Internal `olcrtc` worker restarts made by the supervisor do not change the JWT: they reuse the current in-memory identity. JWT rotation happens when the Python/container service process starts.

Set both values when a stable JWT is required:

```bash
docker run -d \
  --name rupn-server \
  --restart unless-stopped \
  -e 'RUPN_TELEMOST_ROOM=https://telemost.yandex.ru/j/12345678901234' \
  -e 'RUPN_DEVICE_NAME=Maxim iPhone' \
  -e 'RUPN_CLIENT_KEY=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef' \
  -v rupn-server-state:/var/lib/rupn-server \
  makame/rupn-server:latest
```

Generate a key with `openssl rand -hex 32`. If either variable is omitted, that value is regenerated on the next service start and the JWT changes. `RUPN_ROTATE_ON_START=true` forces both values to rotate even when configured, without changing a persisted/fixed room.

`RUPN_KEY_HEX` is supported as a legacy alias for `RUPN_CLIENT_KEY`; `RUPN_CLIENT_ID` is supported as a legacy alias for `RUPN_DEVICE_NAME`. The new names take precedence.

`/var/lib/rupn-server/server.json` stores the current identity and room metadata for inspection. It is replaced from env or regenerated at every service start. Keep the volume private.

## Configuration

| Variable | Default | Description |
|---|---:|---|
| `RUPN_TELEMOST_ROOM` | required | Complete Telemost invite URL or numeric room id. |
| `RUPN_TELEMOST_ROOM_ID` | empty | Legacy alias for `RUPN_TELEMOST_ROOM`. |
| `RUPN_CONNECTION_TYPE` | `telemost` | Connection profile: `telemost` or legacy `wbstream`. |
| `RUPN_LINK` | `direct` | olcrtc link implementation. |
| `RUPN_DNS` | container resolver | Upstream DNS, with optional `:port`. |
| `RUPN_VP8_FPS` | `60` | VP8 frame rate; bounded to `1..60`. |
| `RUPN_VP8_BATCH` | `32` | VP8 batch size; bounded to `32..64`. |
| `RUPN_DEVICE_NAME` | random | Device identity embedded into the URI; 1–128 characters without URI delimiters or controls. |
| `RUPN_CLIENT_KEY` | random | 256-bit key as exactly 64 hexadecimal characters. |
| `RUPN_CLIENT_ID` | empty | Legacy alias for `RUPN_DEVICE_NAME`. |
| `RUPN_KEY_HEX` | empty | Legacy alias for `RUPN_CLIENT_KEY`. |
| `RUPN_JWT_SECRET` | `rupn` | JWT wrapper secret required by compatible clients. |
| `RUPN_DEBUG` | `false` | Enable verbose olcrtc logs. |
| `RUPN_PRINT_RAW_URI` | `false` | Print the secret-bearing raw `olcrtc://` URI. |
| `RUPN_ROTATE_ON_START` | `false` | Force random key and device name even when both are configured. |
| `RUPN_RESTART_BACKOFF_SECONDS` | `2` | Delay after an unexpected olcrtc process exit. |
| `RUPN_SOCKS_PROXY` | empty | Optional upstream SOCKS5 host. |
| `RUPN_SOCKS_PROXY_PORT` | `0` | SOCKS5 port; must be set together with host. |
| `RUPN_TELEMOST_ROOM_FACTORY_URL` | empty | Optional external `POST /v1/rooms` factory used only when no room is supplied. |

### Restart watchdogs

The process is always restarted after an actual exit. Bad-log restarts stay disabled by default. VP8 dataplane recovery is enabled by default because Telemost can expose a remote video track while ingress remains stuck at zero.

| Variable | Default |
|---|---:|
| `RUPN_ENABLE_BAD_LOG_RESTART_WATCHDOG` | `false` |
| `RUPN_BAD_AFTER_SECONDS` | `0` |
| `RUPN_ENABLE_VP8_RESTART_WATCHDOG` | `true` |
| `RUPN_VP8_INGRESS_FROZEN_AFTER_SECONDS` | `60` |
| `RUPN_VP8_ZERO_INGRESS_AFTER_SECONDS` | `30` |
| `RUPN_VP8_RESTART_BACKOFF_SECONDS` | `600` |

Set `RUPN_ENABLE_VP8_RESTART_WATCHDOG=false` to disable dataplane self-heal.

## Optional room factory

The public image does not include browser login or room creation. If you operate a compatible room factory, omit `RUPN_TELEMOST_ROOM` and set `RUPN_TELEMOST_ROOM_FACTORY_URL`; the service must accept `POST /v1/rooms` and return `{"roomUrl":"https://telemost.yandex.ru/j/<id>"}`.

## Build locally

```bash
git clone https://github.com/makamekm/ruvpn-server.git
cd ruvpn-server
docker build --build-arg TARGETARCH=amd64 -t makame/rupn-server:local .
```

## Security

- Treat `RUPN_CONNECT_JWT` as a bearer secret: its payload contains the connection URI and key.
- Do not publish `server.json` or the state volume.
- Do not expose a Docker socket or privileged mode; this container needs neither.
- Pin a released image digest instead of `latest` when reproducibility matters.
