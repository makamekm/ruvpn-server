from __future__ import annotations

import json
import secrets
from dataclasses import asdict
from pathlib import Path

from rupn_server.server_state import ServerState


class ServerStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> ServerState | None:
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return ServerState(
            room_id=str(data["room_id"]),
            key_hex=str(data["key_hex"]),
            client_id=str(data["client_id"]),
            carrier=str(data["carrier"]),
            transport=str(data["transport"]),
        )

    def save(self, state: ServerState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.path)
        self.path.chmod(0o600)

    @staticmethod
    def new_key_hex() -> str:
        return secrets.token_hex(32)
