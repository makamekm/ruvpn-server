from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ServerConfig:
    olcrtc_bin: Path
    data_dir: Path
    state_file: Path
    carrier: str
    transport: str
    link: str
    dns: str
    client_id: str
    jwt_secret: str
    debug: bool
    rotate_on_start: bool
    socks_proxy: str
    socks_proxy_port: int

    @staticmethod
    def load() -> "ServerConfig":
        data_dir = Path(_env("RUPN_DATA_DIR", "/var/lib/rupn-server")).expanduser()
        state_file = Path(_env("RUPN_STATE_FILE", str(data_dir / "server.json"))).expanduser()
        return ServerConfig(
            olcrtc_bin=Path(_env("OLCRTC_BIN", "/usr/local/bin/olcrtc")).expanduser(),
            data_dir=data_dir,
            state_file=state_file,
            carrier=_env("RUPN_CARRIER", "wbstream"),
            transport=_env("RUPN_TRANSPORT", "datachannel"),
            link=_env("RUPN_LINK", "direct"),
            dns=_env("RUPN_DNS", "1.1.1.1:53"),
            client_id=_env("RUPN_CLIENT_ID", "android-01"),
            jwt_secret=_env("RUPN_JWT_SECRET", "rupn"),
            debug=_env_bool("RUPN_DEBUG", False),
            rotate_on_start=_env_bool("RUPN_ROTATE_ON_START", False),
            socks_proxy=_env("RUPN_SOCKS_PROXY", ""),
            socks_proxy_port=_env_int("RUPN_SOCKS_PROXY_PORT", 0),
        )

    def validate(self) -> None:
        if not self.olcrtc_bin.exists():
            raise ValueError(f"OLCRTC_BIN does not exist: {self.olcrtc_bin}")
        if not self.carrier:
            raise ValueError("RUPN_CARRIER is required")
        if not self.transport:
            raise ValueError("RUPN_TRANSPORT is required")
        if not self.client_id:
            raise ValueError("RUPN_CLIENT_ID is required")
        if not self.jwt_secret:
            raise ValueError("RUPN_JWT_SECRET is required")
        if bool(self.socks_proxy) != bool(self.socks_proxy_port):
            raise ValueError("RUPN_SOCKS_PROXY and RUPN_SOCKS_PROXY_PORT must be set together")


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
