# RUPN Server

Public Docker container for running your own RUPN server.

Architecture: one container = one server instance. This repository does not include the private backend, SQLite, Telegram bot, reconciler, node pool, or multi-session orchestration. On startup, the container generates or reuses a single `room/key` pair, starts exactly one `olcrtc -mode srv` process, supervises it, and prints a JWT connection link.

Flow: `ENV → [Validate config] → (missing/invalid env) → [Generate or load room/key] → (room generation error) → [Print JWT link] → [Supervise one server process] → (process exit/bad marker) → [Restart olcrtc] → Ready`

## Quick start

Create a Telemost room, copy its URL, and pass it as `RUPN_TELEMOST_ROOM_ID`:

```bash
docker run --rm -it \
  --name rupn-server \
  -e RUPN_TELEMOST_ROOM_ID='https://telemost.yandex.ru/j/123456789' \
  -v rupn-server-state:/var/lib/rupn-server \
  makame/rupn-server:latest
```

The logs will contain:

```text
RUPN server started
RUPN_CONNECTION_TYPE=telemost
RUPN_CONNECT_JWT=eyJhbG...VCJ9...
RUPN_CONNECT_URI=olcrtc://...
```

Use `RUPN_CONNECT_JWT` in the client app. Replace the example URL with your Telemost room link; `RUPN_TELEMOST_ROOM_ID=123456789` also works.

## Room factory mode

Omit `RUPN_TELEMOST_ROOM_ID` only if you operate a compatible Telemost room-factory service and set `RUPN_TELEMOST_ROOM_FACTORY_URL` to it. The public container itself does not include a browser login/room-factory.

## Docker Compose

```bash
mkdir ruvpn-server
cd ruvpn-server
curl -O https://raw.githubusercontent.com/makamekm/ruvpn-server/main/docker-compose.yml
curl -o .env https://raw.githubusercontent.com/makamekm/ruvpn-server/main/.env.example
# edit .env and set RUPN_TELEMOST_ROOM_ID to your Telemost room id or URL
docker compose up -d
docker logs -f rupn-server
```

## Environment variables

- `RUPN_CONNECTION_TYPE`: connection profile. Allowed: `wbstream`, `telemost`. Default: `telemost`. It selects carrier/transport automatically (`wbstream/datachannel` or `telemost/vp8channel`).
- `RUPN_LINK`: link type. Default: `direct`.
- `RUPN_DNS`: upstream DNS. Default: first nameserver from `/etc/resolv.conf`.
- `RUPN_TELEMOST_ROOM_ID`: existing Telemost room id or full Telemost room URL for `RUPN_CONNECTION_TYPE=telemost`. If set, the server uses it instead of creating a room through the factory.
- `RUPN_TELEMOST_ROOM_FACTORY_URL`: Telemost room factory URL for `RUPN_CONNECTION_TYPE=telemost`. Default: `http://127.0.0.1:8787`.
- `RUPN_VP8_FPS`: VP8 carrier frame rate for `telemost/vp8channel`. Default: `60`.
- `RUPN_VP8_BATCH`: VP8 carrier batch size for `telemost/vp8channel`. Default: `32`; values below `32` are promoted to `32`, values above `64` are clamped to `64`.
- `RUPN_CLIENT_ID`: client id embedded into the connection link. Default: `android-01`.
- `RUPN_JWT_SECRET`: JWT signing secret. Default: `rupn` for compatibility with the Android client.
- `RUPN_DEBUG`: `true/false`, enables olcrtc debug logs.
- `RUPN_ROTATE_ON_START`: `true/false`. Default: `false`, so the connection link is stored in the volume and survives restarts.
- `RUPN_SOCKS_PROXY` + `RUPN_SOCKS_PROXY_PORT`: optional upstream SOCKS5 proxy for server egress.
- `RUPN_BAD_AFTER_SECONDS`: optional stale-log watchdog. Default: `0` disables bad-marker restarts. When set above zero, `ws read error` or `failed to connect link` can restart `olcrtc` after that many seconds. Telemost `publisher/subscriber state: closed` is not treated as fatal by itself.
- `RUPN_VP8_INGRESS_FROZEN_AFTER_SECONDS`: optional VP8 health watchdog for sessions that already saw inbound frames, then `out_frames` keeps growing while `in_frames` stops. Default: `0` disables this restart path.
- `RUPN_VP8_ZERO_INGRESS_AFTER_SECONDS`: optional VP8 health watchdog for sessions that reached a VP8 peer/KCP marker but still have `in_frames=0` while `out_frames` grows. Default: `0` disables this restart path.
- `RUPN_RESTART_BACKOFF_SECONDS`: delay before restarting `olcrtc` after process exit. Default: `2`.

## Rotate the connection link

To issue a new connection link:

```bash
docker run --rm -it \
  -e RUPN_ROTATE_ON_START=true \
  -v rupn-server-state:/var/lib/rupn-server \
  makame/rupn-server:latest
```

Or remove the volume:

```bash
docker compose down -v
docker compose up -d
```

## Build locally

```bash
git clone https://github.com/makamekm/ruvpn-server.git
cd ruvpn-server
docker build -t makame/rupn-server:latest .
docker run --rm -it -v rupn-server-state:/var/lib/rupn-server makame/rupn-server:latest
```

## Security

- Do not publish `RUPN_CONNECT_URI`: it contains the raw key.
- Share `RUPN_CONNECT_JWT` with users.
- If you change `RUPN_JWT_SECRET`, the Android client must use the same secret, otherwise JWT validation will fail.
- The `/var/lib/rupn-server` volume contains `server.json` with the key. Keep it private.
