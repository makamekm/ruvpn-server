from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectionTypeProfile:
    name: str
    carrier: str
    transport: str
