from __future__ import annotations

import subprocess
from typing import Any

from rupn_server.config import ServerConfig
from rupn_server.server_dns_resolver import ServerDnsResolver
from rupn_server.server_state import ServerState


class SingleServerProcess:
    def __init__(self, config: ServerConfig, state: ServerState) -> None:
        self.config = config
        self.state = state

    def command(self) -> list[str]:
        command = [
            str(self.config.olcrtc_bin),
            "-mode",
            "srv",
            "-carrier",
            self.state.carrier,
            "-transport",
            self.state.transport,
            "-id",
            self.state.room_id,
            "-client-id",
            self._server_client_id(self.state.client_id),
            "-key",
            self.state.key_hex,
            "-link",
            self.config.link,
            "-dns",
            ServerDnsResolver.resolve(self.config.dns),
            "-data",
            str(self.config.data_dir),
        ]
        if self.state.transport == "vp8channel":
            command.extend([
                "-vp8-fps",
                str(self.state.vp8_options.fps),
                "-vp8-batch",
                str(self.state.vp8_options.batch),
            ])
        if self.config.socks_proxy:
            command.extend([
                "-socks-proxy",
                self.config.socks_proxy,
                "-socks-proxy-port",
                str(self.config.socks_proxy_port),
            ])
        if self.config.debug:
            command.append("-debug")
        return command

    @staticmethod
    def _server_client_id(client_id: str) -> str:
        # VP8 uses directional client/server binding tokens. The URI keeps the
        # client identity; the server process must use the matching srv- role.
        return client_id if client_id.startswith("srv-") else f"srv-{client_id}"

    def start(self, **popen_kwargs: Any) -> subprocess.Popen[str]:
        return subprocess.Popen(self.command(), text=True, **popen_kwargs)
