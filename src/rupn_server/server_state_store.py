from __future__ import annotations

import json
import secrets
from dataclasses import asdict
from pathlib import Path

from rupn_server.connection_type_registry import ConnectionTypeRegistry
from rupn_server.server_state import ServerState
from rupn_server.vp8_channel_options import Vp8ChannelOptions


class ServerStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> ServerState | None:
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text(encoding="utf-8"))
        connection_type = str(data.get("connection_type") or self._connection_type_from_carrier(str(data["carrier"])))
        vp8_defaults = Vp8ChannelOptions.defaults()
        return ServerState(
            room_id=str(data["room_id"]),
            key_hex=str(data["key_hex"]),
            client_id=str(data["client_id"]),
            carrier=str(data["carrier"]),
            transport=str(data["transport"]),
            connection_type=connection_type,
            vp8_fps=self._int_or_default(data.get("vp8_fps"), vp8_defaults.fps),
            vp8_batch=self._int_or_default(data.get("vp8_batch"), vp8_defaults.batch),
        )

    def save(self, state: ServerState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.path)
        self.path.chmod(0o600)

    @staticmethod
    def _connection_type_from_carrier(carrier: str) -> str:
        for name in ConnectionTypeRegistry.names():
            if ConnectionTypeRegistry.resolve(name).carrier == carrier:
                return name
        return ConnectionTypeRegistry.default().name

    @staticmethod
    def _int_or_default(value: object, default: int) -> int:
        try:
            return int(str(value)) if value is not None and str(value).strip() else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def new_key_hex() -> str:
        return secrets.token_hex(32)
