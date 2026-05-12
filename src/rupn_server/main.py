from __future__ import annotations

import sys

from rupn_server.config import ServerConfig
from rupn_server.connection_token_encoder import ConnectionTokenEncoder
from rupn_server.process_waiter import ProcessWaiter
from rupn_server.room_generator import RoomGenerator
from rupn_server.server_state_factory import ServerStateFactory
from rupn_server.server_state_store import ServerStateStore
from rupn_server.single_server_process import SingleServerProcess


def main() -> int:
    try:
        config = ServerConfig.load()
        config.validate()
        store = ServerStateStore(config.state_file)
        generator = RoomGenerator(config)
        state = ServerStateFactory(config, store, generator).get_or_create()
        token = ConnectionTokenEncoder(config.jwt_secret).encode(state.connection_uri)
        process = SingleServerProcess(config, state).start()
        print("RUPN server started", flush=True)
        print(f"RUPN_CONNECT_JWT={token}", flush=True)
        print(f"RUPN_CONNECT_URI={state.connection_uri}", flush=True)
        return ProcessWaiter(process).wait()
    except Exception as error:  # noqa: BLE001 - entrypoint must print actionable startup errors
        print(f"rupn-server startup failed: {error}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
