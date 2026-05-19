from __future__ import annotations

from dataclasses import dataclass

from rupn_server.vp8_channel_options import Vp8ChannelOptions


@dataclass(frozen=True)
class ServerState:
    room_id: str
    key_hex: str
    client_id: str
    carrier: str
    transport: str
    connection_type: str
    vp8_fps: int
    vp8_batch: int

    @property
    def vp8_options(self) -> Vp8ChannelOptions:
        return Vp8ChannelOptions.bounded(fps=self.vp8_fps, batch=self.vp8_batch)

    @property
    def transport_uri_component(self) -> str:
        if self.transport == "vp8channel":
            return self.vp8_options.transport_suffix
        return self.transport

    @property
    def connection_uri(self) -> str:
        return f"olcrtc://{self.carrier}?{self.transport_uri_component}@{self.room_id}#{self.key_hex}%{self.client_id}$vpnrtc"
