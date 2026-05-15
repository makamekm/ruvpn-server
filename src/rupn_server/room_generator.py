from __future__ import annotations

import subprocess

from rupn_server.config import ServerConfig
from rupn_server.server_dns_resolver import ServerDnsResolver
from rupn_server.telemost_room_factory_client import TelemostRoomFactoryClient


class RoomGenerator:
    def __init__(self, config: ServerConfig) -> None:
        self.config = config

    def generate(self, carrier: str | None = None) -> str:
        selected_carrier = carrier or self.config.carrier
        if selected_carrier == "telemost":
            if self.config.telemost_room_id:
                return self.config.telemost_room_id
            return TelemostRoomFactoryClient(self.config.telemost_room_factory_url).create_room_id()
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                str(self.config.olcrtc_bin),
                "-mode",
                "gen",
                "-carrier",
                selected_carrier,
                "-dns",
                ServerDnsResolver.resolve(self.config.dns),
                "-amount",
                "1",
                "-data",
                str(self.config.data_dir),
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        room_id = result.stdout.strip().splitlines()[-1].strip()
        if not room_id:
            raise RuntimeError(f"olcrtc did not return room id: {result.stderr}")
        return room_id
