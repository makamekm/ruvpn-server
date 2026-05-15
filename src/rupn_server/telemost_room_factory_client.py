from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class TelemostRoomFactoryClient:
    base_url: str
    timeout_seconds: float = 60.0

    def create_room_id(self) -> str:
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/v1/rooms",
            data=b"{}",
            headers={"content-type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as error:
            raise RuntimeError(f"telemost_room_factory_unavailable: {error}") from error
        room_url = str(payload.get("roomUrl", "")).strip()
        room_id = self._extract_room_id(room_url)
        if not room_id:
            raise RuntimeError(f"telemost_room_factory_invalid_room: {room_url}")
        return room_id

    @staticmethod
    def _extract_room_id(room_url: str) -> str:
        candidate = room_url.rstrip("/").rsplit("/", 1)[-1].strip()
        return candidate if candidate.isdigit() else ""
