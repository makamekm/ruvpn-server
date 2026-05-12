from __future__ import annotations

from rupn_server.config import ServerConfig
from rupn_server.room_generator import RoomGenerator
from rupn_server.server_state import ServerState, ServerStateStore


class ServerStateFactory:
    def __init__(self, config: ServerConfig, store: ServerStateStore, generator: RoomGenerator) -> None:
        self.config = config
        self.store = store
        self.generator = generator

    def get_or_create(self) -> ServerState:
        if not self.config.rotate_on_start:
            existing = self.store.load()
            if existing is not None:
                return existing
        state = ServerState(
            room_id=self.generator.generate(),
            key_hex=self.store.new_key_hex(),
            client_id=self.config.client_id,
            carrier=self.config.carrier,
            transport=self.config.transport,
        )
        self.store.save(state)
        return state
