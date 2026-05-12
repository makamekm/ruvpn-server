from __future__ import annotations

import subprocess

from rupn_server.config import ServerConfig


class RoomGenerator:
    def __init__(self, config: ServerConfig) -> None:
        self.config = config

    def generate(self) -> str:
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                str(self.config.olcrtc_bin),
                "-mode",
                "gen",
                "-carrier",
                self.config.carrier,
                "-dns",
                self.config.dns,
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
