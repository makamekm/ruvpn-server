# RUPN client for OpenWrt

The client runs a SOCKS5 listener on the router's loopback interface. LuCI lets you add named connections, check their status and read their logs. Podkop can send selected domains through these connections.

## Start the server

Download `rupn-server-docker.tar.gz` from the [OpenWrt and server release](https://github.com/makamekm/ruvpn-server/releases/tag/openwrt-v0.1.0). The server runs on a Linux AMD64 or ARM64 host with Docker and Docker Compose v2. Create a Telemost meeting and copy its invite link.

```sh
tar -xzf rupn-server-docker.tar.gz
cd rupn-server-docker
umask 077
cp .env.example .env
```

Edit `.env` and set `RUPN_TELEMOST_ROOM` to the invite link. Set `RUPN_DEVICE_NAME` and `RUPN_CLIENT_KEY` to keep the same client token after a restart. Generate a key with `openssl rand -hex 32`.

```sh
docker compose up -d --build
docker compose logs rupn-server
```

Copy the value of `RUPN_CONNECT_JWT` from the logs. Keep the token private. The default configuration needs outbound internet access on the server. For additional simultaneous clients, use separate server instances and rooms.

To build from a checkout of this repository, use `docker compose -f docker-compose.build.yml up -d --build` with the same `.env` setup.

## Install on the router

The router needs OpenWrt with LuCI and root SSH access. Install the router packages `curl`, `jq` and `flock` with its package manager. The installer also uses `uci`, `ubus` and `rpcd`, which are part of the OpenWrt and LuCI setup.

- `uname -m` reports `aarch64`. Download `rupn-openwrt-aarch64.tar.gz`.
- `uname -m` reports `x86_64`. Download `rupn-openwrt-x86_64.tar.gz`.

From a computer on the router's network, unpack the matching release archive and run the installer. Replace the example SSH address with your router's LAN address.

```sh
tar -xzf rupn-openwrt-aarch64.tar.gz
cd rupn-openwrt-aarch64
sh ./install-luci.sh --binary ./rupn root@192.168.1.1
```

1. Open **Status → RUPN** in LuCI.
2. Add a connection and paste the server's **RUPN_CONNECT_JWT** value into the key field. Enable and save the connection.
3. Wait for the profile to be ready, then use its connectivity check. Select the profile in the logs section to troubleshoot a failure.

An upgrade keeps saved profiles. The installer migrates a legacy `/etc/rupn/token` into the first profile on port 17808.

## Route domains in Podkop

Create or edit a section, choose **Proxy**, then **Connection URL**. Select the profile under **RUPN connection**. Keep the domains that should use the tunnel in that section, then click **Save & Apply**. For a first check, add `example.com`.

If the picker is unavailable, copy that profile's SOCKS5 URL from **Status → RUPN**. A typical first profile uses `socks5://127.0.0.1:17808`. Each additional profile has its own port. After upgrading Podkop, rerun the LuCI installer to restore the picker if necessary.

## Build from source

Use Go 1.25 or later and revision `7ead0d28afec3cfd0f919343da8bbd408d6d657e` of the [RUPN fork of olcRTC](https://github.com/makamekm/olcrtc). Put the olcRTC checkout next to this repository or set `OLCRTC_ROOT` to its path.

```sh
RUPN_ARCH=arm64 ./openwrt/build.sh /tmp/rupn-build
sh ./openwrt/install-luci.sh --binary /tmp/rupn-build/rupn root@192.168.1.1
```

Use `RUPN_ARCH=amd64` for x86-64. The result is a static Linux executable named `rupn`.
