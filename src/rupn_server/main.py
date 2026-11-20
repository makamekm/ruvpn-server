from __future__ import annotations

import os
import sys

from rupn_server.config import ServerConfig
from rupn_server.connection_token_encoder import ConnectionTokenEncoder
from rupn_server.lan_access import LanAccess
from rupn_server.room_generator import RoomGenerator
from rupn_server.server_state_factory import ServerStateFactory
from rupn_server.server_state_store import ServerStateStore
from rupn_server.server_supervisor import ServerSupervisor
from rupn_server.server_dns_resolver import ServerDnsResolver


def main() -> int:
    try:
        config = ServerConfig.load()
        config.validate()
        store = ServerStateStore(config.state_file)
        generator = RoomGenerator(config)
        state = ServerStateFactory(config, store, generator).get_or_create()
        dns_server = ServerDnsResolver.resolve(config.dns)
        lan_subnets = LanAccess.resolve(config.lan_access, config.lan_subnets, dns_server)
        # olcrtc reads the exposed subnets from its environment.
        os.environ["OLCRTC_LAN_SUBNETS"] = lan_subnets
        _export_direct_path(config)
        connection_uri = state.connection_uri_with_dns(dns_server, lan_subnets)
        token = ConnectionTokenEncoder(config.jwt_secret).encode(connection_uri)
        print("RUPN server started", flush=True)
        print(f"RUPN_CONNECTION_TYPE={state.connection_type}", flush=True)
        print(f"RUPN_TELEMOST_ROOM_ID={state.room_id}", flush=True)
        print(f"RUPN_DEVICE_NAME={state.client_id}", flush=True)
        print(f"RUPN_LAN_SUBNETS={lan_subnets or 'off'}", flush=True)
        print(f"RUPN_DIRECT_PORT={config.direct_port or 'off'}", flush=True)
        print(f"RUPN_CONNECT_JWT={token}", flush=True)
        if config.print_raw_uri:
            print(f"RUPN_CONNECT_URI={connection_uri}", flush=True)
        return ServerSupervisor(config, state).run()
    except Exception as error:  # noqa: BLE001 - entrypoint must print actionable startup errors
        print(f"rupn-server startup failed: {error}", file=sys.stderr, flush=True)
        return 1


def _export_direct_path(config: ServerConfig) -> None:
    """Pass direct peer-to-peer path settings to olcrtc (off when port is 0)."""
    if not 0 < config.direct_port < 65536:
        os.environ.pop("OLCRTC_DIRECT_PORT", None)
        return
    os.environ["OLCRTC_DIRECT_PORT"] = str(config.direct_port)
    os.environ["OLCRTC_DIRECT_NATPMP"] = "1" if config.direct_natpmp else "0"
    if config.direct_public_ip:
        os.environ["OLCRTC_DIRECT_PUBLIC_IP"] = config.direct_public_ip


if __name__ == "__main__":
    raise SystemExit(main())
