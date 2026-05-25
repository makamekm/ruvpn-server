import json
from email.message import Message
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch

import pytest

from rupn_server.connection_type_registry import ConnectionTypeRegistry
from rupn_server.server_dns_resolver import ServerDnsResolver
from rupn_server.telemost_room_factory_client import TelemostRoomFactoryClient
from rupn_server.vp8_channel_options import Vp8ChannelOptions


def test_vp8_defaults_match_android_reference_contract():
    defaults = Vp8ChannelOptions.defaults()
    assert defaults.fps == 60
    assert defaults.batch == 16
    assert defaults.transport_suffix == "vp8channel<vp8-fps=60&vp8-batch=16>"


def test_vp8_options_are_clamped_to_supported_bounds():
    bounded = Vp8ChannelOptions.bounded(fps=120, batch=999)
    assert bounded.fps == 60
    assert bounded.batch == 16


def test_connection_profiles_are_platform_neutral():
    telemost = ConnectionTypeRegistry.resolve("telemost")
    assert telemost.carrier == "telemost"
    assert telemost.transport == "vp8channel"
    assert "ios" not in telemost.transport.lower()
    assert "android" not in telemost.transport.lower()


def test_default_connection_type_matches_closed_backend_contract():
    assert ConnectionTypeRegistry.default().name == "telemost"


def test_dns_resolver_prefers_ipv4_nameserver(tmp_path: Path):
    resolv_conf = tmp_path / "resolv.conf"
    resolv_conf.write_text("nameserver 2001:4860:4860::8888\nnameserver 10.0.0.53\n", encoding="utf-8")

    assert ServerDnsResolver.resolve(resolv_conf_path=resolv_conf) == "10.0.0.53:53"


def test_dns_resolver_falls_back_when_resolv_conf_missing(tmp_path: Path):
    assert ServerDnsResolver.resolve(resolv_conf_path=tmp_path / "missing.conf") == "1.1.1.1:53"


def test_telemost_factory_auth_error_is_actionable():
    payload = {"error": "telemost_auth_required", "message": "login required"}
    error = HTTPError(
        url="http://127.0.0.1:8787/v1/rooms",
        code=401,
        msg="Unauthorized",
        hdrs=Message(),
        fp=BytesIO(json.dumps(payload).encode("utf-8")),
    )

    with patch("urllib.request.urlopen", side_effect=error), pytest.raises(RuntimeError) as raised:
        TelemostRoomFactoryClient("http://127.0.0.1:8787").create_room_id()

    assert "telemost_auth_required" in str(raised.value)
    assert "noVNC room-factory" in str(raised.value)
