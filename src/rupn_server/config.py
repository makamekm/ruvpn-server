from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from rupn_server.connection_type_profile import ConnectionTypeProfile
from rupn_server.connection_type_registry import ConnectionTypeRegistry
from rupn_server.vp8_channel_options import Vp8ChannelOptions


@dataclass(frozen=True)
class ServerConfig:
    olcrtc_bin: Path
    data_dir: Path
    state_file: Path
    connection_type: ConnectionTypeProfile
    carrier: str
    transport: str
    link: str
    dns: str
    client_id: str
    jwt_secret: str
    telemost_room_id: str
    telemost_room_factory_url: str
    vp8_options: Vp8ChannelOptions
    debug: bool
    rotate_on_start: bool
    socks_proxy: str
    socks_proxy_port: int
    bad_after_seconds: float
    restart_backoff_seconds: float

    @staticmethod
    def load() -> "ServerConfig":
        data_dir = Path(_env("RUPN_DATA_DIR", "/var/lib/rupn-server")).expanduser()
        state_file = Path(_env("RUPN_STATE_FILE", str(data_dir / "server.json"))).expanduser()
        connection_type = ConnectionTypeRegistry.resolve(_env("RUPN_CONNECTION_TYPE", ConnectionTypeRegistry.default().name))
        vp8_defaults = Vp8ChannelOptions.defaults()
        return ServerConfig(
            olcrtc_bin=Path(_env("OLCRTC_BIN", "/usr/local/bin/olcrtc")).expanduser(),
            data_dir=data_dir,
            state_file=state_file,
            connection_type=connection_type,
            carrier=connection_type.carrier,
            transport=connection_type.transport,
            link=_env("RUPN_LINK", "direct"),
            dns=_env("RUPN_DNS", ""),
            client_id=_env("RUPN_CLIENT_ID", "android-01"),
            jwt_secret=_env("RUPN_JWT_SECRET", "rupn"),
            telemost_room_id=_env("RUPN_TELEMOST_ROOM_ID", ""),
            telemost_room_factory_url=_env("RUPN_TELEMOST_ROOM_FACTORY_URL", "http://127.0.0.1:8787"),
            vp8_options=Vp8ChannelOptions.bounded(
                fps=_env_int("RUPN_VP8_FPS", vp8_defaults.fps),
                batch=_env_int("RUPN_VP8_BATCH", vp8_defaults.batch),
            ),
            debug=_env_bool("RUPN_DEBUG", False),
            rotate_on_start=_env_bool("RUPN_ROTATE_ON_START", False),
            socks_proxy=_env("RUPN_SOCKS_PROXY", ""),
            socks_proxy_port=_env_int("RUPN_SOCKS_PROXY_PORT", 0),
            bad_after_seconds=_env_float("RUPN_BAD_AFTER_SECONDS", 0.0),
            restart_backoff_seconds=_env_float("RUPN_RESTART_BACKOFF_SECONDS", 2.0),
        )

    def validate(self) -> None:
        if not self.olcrtc_bin.exists():
            raise ValueError(f"OLCRTC_BIN does not exist: {self.olcrtc_bin}")
        if not self.carrier:
            raise ValueError("RUPN_CARRIER is required")
        if not self.transport:
            raise ValueError("RUPN_TRANSPORT is required")
        if self.connection_type.name == "telemost" and not self.telemost_room_id and not self.telemost_room_factory_url:
            raise ValueError("RUPN_TELEMOST_ROOM_ID or RUPN_TELEMOST_ROOM_FACTORY_URL is required for telemost")
        if not self.client_id:
            raise ValueError("RUPN_CLIENT_ID is required")
        if not self.jwt_secret:
            raise ValueError("RUPN_JWT_SECRET is required")
        if bool(self.socks_proxy) != bool(self.socks_proxy_port):
            raise ValueError("RUPN_SOCKS_PROXY and RUPN_SOCKS_PROXY_PORT must be set together")
        if self.restart_backoff_seconds < 0:
            raise ValueError("RUPN_RESTART_BACKOFF_SECONDS must be non-negative")


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return float(value)
