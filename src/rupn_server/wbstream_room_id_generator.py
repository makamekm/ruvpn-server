from __future__ import annotations

import secrets


class WbstreamRoomIdGenerator:
    @staticmethod
    def generate() -> str:
        return str(10_000_000_000_000 + secrets.randbelow(90_000_000_000_000))
