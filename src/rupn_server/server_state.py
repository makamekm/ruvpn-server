from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ServerState:
    room_id: str
    key_hex: str
    client_id: str
    carrier: str
    transport: str

    @property
    def connection_uri(self) -> str:
        return f"olcrtc://{self.carrier}?{self.transport}@{self.room_id}#{self.key_hex}%{self.client_id}$vpnrtc"
