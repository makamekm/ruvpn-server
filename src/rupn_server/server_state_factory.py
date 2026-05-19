from __future__ import annotations

from dataclasses import replace

from rupn_server.config import ServerConfig
from rupn_server.room_generator import RoomGenerator
from rupn_server.server_state import ServerState
from rupn_server.server_state_store import ServerStateStore


class ServerStateFactory:
    def __init__(self, config: ServerConfig, store: ServerStateStore, generator: RoomGenerator) -> None:
        self.config = config
        self.store = store
        self.generator = generator

    def get_or_create(self) -> ServerState:
        if not self.config.rotate_on_start:
            existing = self.store.load()
            if existing is not None and existing.connection_type == self.config.connection_type.name:
                return self._with_runtime_options(existing)
        state = ServerState(
            room_id=self.generator.generate(carrier=self.config.connection_type.carrier),
            key_hex=self.store.new_key_hex(),
            client_id=self.config.client_id,
            carrier=self.config.connection_type.carrier,
            transport=self.config.connection_type.transport,
            connection_type=self.config.connection_type.name,
            vp8_fps=self.config.vp8_options.fps,
            vp8_batch=self.config.vp8_options.batch,
        )
        self.store.save(state)
        return state

    def _with_runtime_options(self, state: ServerState) -> ServerState:
        updated = replace(
            state,
            vp8_fps=self.config.vp8_options.fps,
            vp8_batch=self.config.vp8_options.batch,
        )
        if updated != state:
            self.store.save(updated)
        return updated
