from __future__ import annotations

import json
import re
import stat
from pathlib import Path

import pytest

from rupn_server.config import ServerConfig
from rupn_server.connection_token_encoder import ConnectionTokenEncoder
from rupn_server.room_generator import RoomGenerator
from rupn_server.server_state import ServerState
from rupn_server.server_state_factory import ServerStateFactory
from rupn_server.server_state_store import ServerStateStore


def _config(monkeypatch, tmp_path: Path, room: str) -> ServerConfig:
    binary = tmp_path / "olcrtc"
    binary.write_text("", encoding="utf-8")
    monkeypatch.setenv("OLCRTC_BIN", str(binary))
    monkeypatch.setenv("RUPN_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RUPN_TELEMOST_ROOM", room)
    monkeypatch.setenv("RUPN_DEVICE_NAME", "")
    monkeypatch.setenv("RUPN_CLIENT_KEY", "")
    monkeypatch.setenv("RUPN_KEY_HEX", "")
    monkeypatch.setenv("RUPN_CLIENT_ID", "")
    monkeypatch.setenv("RUPN_ROTATE_ON_START", "false")
    return ServerConfig.load()


def _state(config: ServerConfig) -> ServerState:
    store = ServerStateStore(config.state_file)
    return ServerStateFactory(config, store, RoomGenerator(config)).get_or_create()


def _token(config: ServerConfig, state: ServerState) -> str:
    return ConnectionTokenEncoder(config.jwt_secret).encode(state.connection_uri)


def test_restart_without_identity_env_rotates_key_device_and_jwt(monkeypatch, tmp_path: Path):
    first_config = _config(monkeypatch, tmp_path, "22222222222222")
    first = _state(first_config)
    second_config = ServerConfig.load()
    second = _state(second_config)

    assert first.room_id == second.room_id == "22222222222222"
    assert first.key_hex != second.key_hex
    assert first.client_id != second.client_id
    assert _token(first_config, first) != _token(second_config, second)
    assert re.fullmatch(r"[0-9a-f]{64}", second.key_hex)
    assert re.fullmatch(r"device-[0-9a-f]{16}", second.client_id)
    assert ServerStateStore(second_config.state_file).load() == second


def test_explicit_key_and_device_name_keep_jwt_stable_across_restart(monkeypatch, tmp_path: Path):
    _config(monkeypatch, tmp_path, "22222222222222")
    monkeypatch.setenv("RUPN_DEVICE_NAME", "Maxim iPhone")
    monkeypatch.setenv("RUPN_CLIENT_KEY", "AB" * 32)
    first_config = ServerConfig.load()
    first = _state(first_config)
    second_config = ServerConfig.load()
    second = _state(second_config)

    assert first.key_hex == second.key_hex == "ab" * 32
    assert first.client_id == second.client_id == "Maxim iPhone"
    assert _token(first_config, first) == _token(second_config, second)


@pytest.mark.parametrize("fixed_field", ["key", "name"])
def test_partially_configured_identity_rotates_only_missing_value(monkeypatch, tmp_path: Path, fixed_field: str):
    _config(monkeypatch, tmp_path, "22222222222222")
    if fixed_field == "key":
        monkeypatch.setenv("RUPN_CLIENT_KEY", "ab" * 32)
    else:
        monkeypatch.setenv("RUPN_DEVICE_NAME", "Maxim iPhone")

    first_config = ServerConfig.load()
    first = _state(first_config)
    second_config = ServerConfig.load()
    second = _state(second_config)

    if fixed_field == "key":
        assert first.key_hex == second.key_hex == "ab" * 32
        assert first.client_id != second.client_id
    else:
        assert first.client_id == second.client_id == "Maxim iPhone"
        assert first.key_hex != second.key_hex
    assert _token(first_config, first) != _token(second_config, second)


def test_rotate_on_start_overrides_explicit_identity_without_changing_room(monkeypatch, tmp_path: Path):
    _config(monkeypatch, tmp_path, "22222222222222")
    monkeypatch.setenv("RUPN_DEVICE_NAME", "maxim-phone")
    monkeypatch.setenv("RUPN_CLIENT_KEY", "ab" * 32)
    first_config = ServerConfig.load()
    first = _state(first_config)

    monkeypatch.setenv("RUPN_ROTATE_ON_START", "true")
    second_config = ServerConfig.load()
    second = _state(second_config)

    assert first.client_id == "maxim-phone"
    assert first.key_hex == "ab" * 32
    assert second.room_id == first.room_id
    assert second.client_id != "maxim-phone"
    assert second.key_hex != "ab" * 32
    assert _token(first_config, first) != _token(second_config, second)


def test_fixed_room_replaces_persisted_room_and_randomizes_identity(monkeypatch, tmp_path: Path):
    config = _config(monkeypatch, tmp_path, "https://telemost.yandex.ru/j/22222222222222")
    store = ServerStateStore(config.state_file)
    store.save(
        ServerState(
            room_id="11111111111111",
            key_hex="11" * 32,
            client_id="old-client",
            carrier="telemost",
            transport="vp8channel",
            connection_type="telemost",
            vp8_fps=25,
            vp8_batch=32,
        )
    )

    state = ServerStateFactory(config, store, RoomGenerator(config)).get_or_create()

    assert state.room_id == "22222222222222"
    assert state.key_hex == config.client_key
    assert state.key_hex != "11" * 32
    assert state.client_id == config.client_id
    assert state.client_id != "old-client"
    assert store.load() == state


def test_legacy_aliases_and_new_variable_precedence(monkeypatch, tmp_path: Path):
    _config(monkeypatch, tmp_path, "33333333333333")
    monkeypatch.setenv("RUPN_TELEMOST_ROOM", "")
    monkeypatch.setenv("RUPN_TELEMOST_ROOM_ID", "44444444444444")
    monkeypatch.setenv("RUPN_CLIENT_ID", "legacy-device")
    monkeypatch.setenv("RUPN_KEY_HEX", "11" * 32)

    legacy = ServerConfig.load()
    assert legacy.telemost_room_id == "44444444444444"
    assert legacy.client_id == "legacy-device"
    assert legacy.client_key == "11" * 32

    monkeypatch.setenv("RUPN_DEVICE_NAME", "new-device")
    monkeypatch.setenv("RUPN_CLIENT_KEY", "22" * 32)
    current = ServerConfig.load()
    assert current.client_id == "new-device"
    assert current.client_key == "22" * 32


def test_real_legacy_state_json_is_migrated_but_identity_rotates(monkeypatch, tmp_path: Path):
    config = _config(monkeypatch, tmp_path, "22222222222222")
    config.state_file.parent.mkdir(parents=True, exist_ok=True)
    config.state_file.write_text(
        json.dumps(
            {
                "room_id": "11111111111111",
                "key_hex": "22" * 32,
                "client_id": "old-client",
                "carrier": "telemost",
                "transport": "vp8channel",
            }
        ),
        encoding="utf-8",
    )

    state = _state(config)

    assert state.room_id == "22222222222222"
    assert state.key_hex == config.client_key
    assert state.key_hex != "22" * 32
    assert state.client_id == config.client_id
    assert state.connection_type == "telemost"
    assert state.vp8_fps == 60
    assert state.vp8_batch == 32
    assert stat.S_IMODE(config.state_file.stat().st_mode) == 0o600


@pytest.mark.parametrize(
    ("key", "name", "message"),
    [
        ("short", "valid-name", "RUPN_CLIENT_KEY"),
        ("ab" * 32, "invalid%name", "RUPN_DEVICE_NAME"),
    ],
)
def test_invalid_explicit_identity_is_rejected(monkeypatch, tmp_path: Path, key: str, name: str, message: str):
    _config(monkeypatch, tmp_path, "55555555555555")
    monkeypatch.setenv("RUPN_CLIENT_KEY", key)
    monkeypatch.setenv("RUPN_DEVICE_NAME", name)

    with pytest.raises(ValueError, match=message):
        ServerConfig.load().validate()


def test_watchdog_restart_defaults_match_self_host_recovery_contract(monkeypatch, tmp_path: Path):
    config = _config(monkeypatch, tmp_path, "55555555555555")

    assert config.enable_bad_log_restart_watchdog is False
    assert config.enable_vp8_restart_watchdog is True
    assert config.vp8_ingress_frozen_after_seconds == 60
    assert config.vp8_zero_ingress_after_seconds == 30
    assert config.vp8_restart_backoff_seconds == 600

    monkeypatch.setenv("RUPN_ENABLE_VP8_RESTART_WATCHDOG", "false")
    assert ServerConfig.load().enable_vp8_restart_watchdog is False


def test_lan_access_is_off_unless_enabled():
    from rupn_server.lan_access import LanAccess

    assert LanAccess.resolve(False, "192.168.0.0/24", "192.168.0.191:53") == ""


def test_lan_access_derives_home_subnet_from_private_dns():
    from rupn_server.lan_access import LanAccess

    assert LanAccess.resolve(True, "", "192.168.0.191:53") == "192.168.0.0/24"
    # A public or loopback resolver (cloud server) yields nothing to expose.
    assert LanAccess.resolve(True, "", "1.1.1.1:53") == ""
    assert LanAccess.resolve(True, "", "127.0.0.11:53") == ""


def test_lan_access_keeps_only_private_configured_subnets():
    from rupn_server.lan_access import LanAccess

    spec = LanAccess.resolve(True, "10.1.0.0/16, 8.8.8.0/24, junk, 192.168.5.7/24", "1.1.1.1:53")
    assert spec == "10.1.0.0/16,192.168.5.0/24"


def test_connection_uri_carries_lan_subnets():
    from rupn_server.server_state import ServerState

    state = ServerState(
        room_id="123", key_hex="ab" * 32, client_id="dev-123", carrier="telemost",
        transport="vp8channel", connection_type="telemost", vp8_fps=60, vp8_batch=32,
    )
    with_lan = state.connection_uri_with_dns("192.168.0.191:53", "192.168.0.0/24")
    assert "dns=192.168.0.191%3A53&lan=192.168.0.0%2F24>" in with_lan
    assert "lan=" not in state.connection_uri_with_dns("192.168.0.191:53")


def test_direct_path_env_is_exported_only_when_enabled(monkeypatch):
    import os
    from types import SimpleNamespace

    from rupn_server.main import _export_direct_path

    monkeypatch.delenv("OLCRTC_DIRECT_PORT", raising=False)
    _export_direct_path(SimpleNamespace(direct_port=0, direct_natpmp=True, direct_public_ip=""))
    assert "OLCRTC_DIRECT_PORT" not in os.environ
    _export_direct_path(SimpleNamespace(direct_port=40400, direct_natpmp=False, direct_public_ip="203.0.113.5"))
    assert os.environ["OLCRTC_DIRECT_PORT"] == "40400"
    assert os.environ["OLCRTC_DIRECT_NATPMP"] == "0"
    assert os.environ["OLCRTC_DIRECT_PUBLIC_IP"] == "203.0.113.5"
    monkeypatch.delenv("OLCRTC_DIRECT_PORT", raising=False)
    monkeypatch.delenv("OLCRTC_DIRECT_NATPMP", raising=False)
    monkeypatch.delenv("OLCRTC_DIRECT_PUBLIC_IP", raising=False)
