from __future__ import annotations

import subprocess

from rupn_server.config import ServerConfig
from rupn_server.server_state import ServerState


class SingleServerProcess:
    def __init__(self, config: ServerConfig, state: ServerState) -> None:
        self.config = config
        self.state = state

    def start(self) -> subprocess.Popen[str]:
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
            self.state.client_id,
            "-key",
            self.state.key_hex,
            "-link",
            self.config.link,
            "-dns",
            self.config.dns,
            "-data",
            str(self.config.data_dir),
        ]
        if self.config.socks_proxy:
            command.extend(["-socks-proxy", self.config.socks_proxy, "-socks-proxy-port", str(self.config.socks_proxy_port)])
        if self.config.debug:
            command.append("-debug")
        return subprocess.Popen(command, text=True)
