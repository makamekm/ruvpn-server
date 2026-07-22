from __future__ import annotations

import re
from urllib.parse import unquote, urlparse


_ROOM_ID_RE = re.compile(r"^[0-9]{3,128}$")


def parse_telemost_room(value: str) -> str:
    """Return a Telemost room id from either an id or a complete invite URL."""
    candidate = value.strip()
    if not candidate:
        return ""
    if "://" in candidate:
        parsed = urlparse(candidate)
        if parsed.scheme != "https" or parsed.hostname not in {
            "telemost.yandex.ru",
            "telemost.360.yandex.ru",
        }:
            raise ValueError("RUPN_TELEMOST_ROOM must be a Telemost room id or an https Telemost invite URL")
        path_parts = [unquote(part).strip() for part in parsed.path.split("/") if part.strip()]
        if len(path_parts) != 2 or path_parts[0] != "j":
            raise ValueError("RUPN_TELEMOST_ROOM contains an invalid Telemost invite URL")
        candidate = path_parts[1]
    candidate = candidate.strip().strip("/")
    if not _ROOM_ID_RE.fullmatch(candidate):
        raise ValueError("RUPN_TELEMOST_ROOM contains an invalid Telemost room id")
    return candidate
