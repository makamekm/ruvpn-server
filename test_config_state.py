from __future__ import annotations

import json
from pathlib import Path

import pytest

from rupn_server.config import ServerConfig
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
    return ServerConfig.load()


def _fixed_generated_credentials(monkeypatch, *, key_hex: str = "aa" * 32, device_name: str = "device-random") -> None:
    monkeypatch.setattr(ServerStateStore, "new_key_hex", staticmethod(lambda: key_hex))
    monkeypatch.setattr(ServerStateStore, "new_device_name", staticmethod(lambda: device_name))


def test_fixed_telemost_room_replaces_persisted_room_and_rotates_unpinned_credentials(monkeypatch, tmp_path: Path):
    _fixed_generated_credentials(monkeypatch)
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
            vp8_batch=1,
        )
    )

    state = ServerStateFactory(config, store, RoomGenerator(config)).get_or_create()

    assert state.room_id == "22222222222222"
    assert state.key_hex == "aa" * 32
    assert state.client_id == "device-random"
    assert store.load() == state


def test_env_key_and_device_pin_jwt_credentials_across_restarts(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("RUPN_KEY_HEX", "33" * 32)
    monkeypatch.setenv("RUPN_DEVICE_NAME", "max-phone")
    config = _config(monkeypatch, tmp_path, "https://telemost.yandex.ru/j/22222222222222")
    store = ServerStateStore(config.state_file)

    first = ServerStateFactory(config, store, RoomGenerator(config)).get_or_create()
    second = ServerStateFactory(config, store, RoomGenerator(config)).get_or_create()

    assert first == second
    assert first.key_hex == "33" * 32
    assert first.client_id == "max-phone"
    assert "%max-phone$vpnrtc" in first.connection_uri


def test_unpinned_key_and_device_rotate_on_every_service_start_even_with_volume(monkeypatch, tmp_path: Path):
    generated = iter([("aa" * 32, "device-one"), ("bb" * 32, "device-two")])
    current = {"pair": next(generated)}
    monkeypatch.setattr(ServerStateStore, "new_key_hex", staticmethod(lambda: current["pair"][0]))
    monkeypatch.setattr(ServerStateStore, "new_device_name", staticmethod(lambda: current["pair"][1]))
    config = _config(monkeypatch, tmp_path, "https://telemost.yandex.ru/j/22222222222222")
    store = ServerStateStore(config.state_file)

    first = ServerStateFactory(config, store, RoomGenerator(config)).get_or_create()
    current["pair"] = next(generated)
    second = ServerStateFactory(config, store, RoomGenerator(config)).get_or_create()

    assert first.room_id == second.room_id == "22222222222222"
    assert first.key_hex == "aa" * 32
    assert first.client_id == "device-one"
    assert second.key_hex == "bb" * 32
    assert second.client_id == "device-two"
    assert first.connection_uri != second.connection_uri


def test_legacy_room_id_alias_works_when_new_variable_is_empty(monkeypatch, tmp_path: Path):
    binary = tmp_path / "olcrtc"
    binary.write_text("", encoding="utf-8")
    monkeypatch.setenv("OLCRTC_BIN", str(binary))
    monkeypatch.setenv("RUPN_TELEMOST_ROOM", "")
    monkeypatch.setenv("RUPN_TELEMOST_ROOM_ID", "33333333333333")

    assert ServerConfig.load().telemost_room_id == "33333333333333"


def test_device_name_env_precedes_legacy_client_id_alias(monkeypatch, tmp_path: Path):
    binary = tmp_path / "olcrtc"
    binary.write_text("", encoding="utf-8")
    monkeypatch.setenv("OLCRTC_BIN", str(binary))
    monkeypatch.setenv("RUPN_TELEMOST_ROOM", "33333333333333")
    monkeypatch.setenv("RUPN_DEVICE_NAME", "phone-main")
    monkeypatch.setenv("RUPN_CLIENT_ID", "legacy-client")

    assert ServerConfig.load().client_id == "phone-main"


def test_legacy_client_id_alias_still_pins_device_name(monkeypatch, tmp_path: Path):
    binary = tmp_path / "olcrtc"
    binary.write_text("", encoding="utf-8")
    monkeypatch.setenv("OLCRTC_BIN", str(binary))
    monkeypatch.setenv("RUPN_TELEMOST_ROOM", "33333333333333")
    monkeypatch.setenv("RUPN_DEVICE_NAME", "")
    monkeypatch.setenv("RUPN_CLIENT_ID", "legacy-client")

    assert ServerConfig.load().client_id == "legacy-client"


def test_real_legacy_state_json_is_migrated_but_unpinned_credentials_rotate(monkeypatch, tmp_path: Path):
    _fixed_generated_credentials(monkeypatch, key_hex="cc" * 32, device_name="device-fresh")
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

    state = ServerStateFactory(config, ServerStateStore(config.state_file), RoomGenerator(config)).get_or_create()

    assert state.room_id == "22222222222222"
    assert state.key_hex == "cc" * 32
    assert state.client_id == "device-fresh"
    assert state.connection_type == "telemost"
    assert state.vp8_fps == 60
    assert state.vp8_batch == 32


def test_key_hex_validation(monkeypatch, tmp_path: Path):
    config = _config(monkeypatch, tmp_path, "22222222222222")
    assert config.key_hex == ""

    monkeypatch.setenv("RUPN_KEY_HEX", "AA" * 32)
    uppercase = ServerConfig.load()
    uppercase.validate()
    assert uppercase.key_hex == "aa" * 32

    monkeypatch.setenv("RUPN_KEY_HEX", "not-hex")
    invalid = ServerConfig.load()
    with pytest.raises(ValueError, match="RUPN_KEY_HEX"):
        invalid.validate()


def test_device_name_validation(monkeypatch, tmp_path: Path):
    _config(monkeypatch, tmp_path, "22222222222222")
    monkeypatch.setenv("RUPN_DEVICE_NAME", "bad device name")
    invalid = ServerConfig.load()
    with pytest.raises(ValueError, match="RUPN_DEVICE_NAME"):
        invalid.validate()


def test_watchdog_restart_defaults_match_self_host_recovery_contract(monkeypatch, tmp_path: Path):
    config = _config(monkeypatch, tmp_path, "55555555555555")

    assert config.enable_bad_log_restart_watchdog is False
    assert config.enable_vp8_restart_watchdog is True
    assert config.vp8_ingress_frozen_after_seconds == 60
    assert config.vp8_zero_ingress_after_seconds == 30
    assert config.vp8_restart_backoff_seconds == 600

    monkeypatch.setenv("RUPN_BAD_AFTER_SECONDS", "20")
    monkeypatch.setenv("RUPN_ENABLE_VP8_RESTART_WATCHDOG", "false")
    disabled = ServerConfig.load()
    assert disabled.enable_vp8_restart_watchdog is False

    monkeypatch.setenv("RUPN_ENABLE_BAD_LOG_RESTART_WATCHDOG", "true")
    enabled = ServerConfig.load()
    assert enabled.enable_bad_log_restart_watchdog is True
    assert enabled.enable_vp8_restart_watchdog is False
