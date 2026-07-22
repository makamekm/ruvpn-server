from __future__ import annotations

import json
from pathlib import Path

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


def test_fixed_telemost_room_replaces_persisted_room_without_rotate(monkeypatch, tmp_path: Path):
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
    assert state.key_hex == "11" * 32
    assert state.client_id == config.client_id
    assert store.load() == state


def test_legacy_room_id_alias_works_when_new_variable_is_empty(monkeypatch, tmp_path: Path):
    binary = tmp_path / "olcrtc"
    binary.write_text("", encoding="utf-8")
    monkeypatch.setenv("OLCRTC_BIN", str(binary))
    monkeypatch.setenv("RUPN_TELEMOST_ROOM", "")
    monkeypatch.setenv("RUPN_TELEMOST_ROOM_ID", "33333333333333")

    assert ServerConfig.load().telemost_room_id == "33333333333333"


def test_real_legacy_state_json_is_migrated_and_keeps_key(monkeypatch, tmp_path: Path):
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
    assert state.key_hex == "22" * 32
    assert state.connection_type == "telemost"
    assert state.vp8_fps == 60
    assert state.vp8_batch == 32


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
