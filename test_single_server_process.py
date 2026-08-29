from pathlib import Path
from types import SimpleNamespace
from typing import cast

from rupn_server.config import ServerConfig
from rupn_server.server_state import ServerState
from rupn_server.single_server_process import SingleServerProcess


def test_server_command_uses_srv_role_but_connection_uri_keeps_client_identity():
    config = cast(
        ServerConfig,
        SimpleNamespace(
            olcrtc_bin=Path("/usr/local/bin/olcrtc"),
            link="direct",
            dns="1.1.1.1",
            data_dir=Path("/tmp/rupn"),
            socks_proxy="",
            socks_proxy_port=0,
            debug=False,
        ),
    )
    state = ServerState(
        room_id="18209719117887",
        key_hex="11" * 32,
        client_id="android-01",
        carrier="telemost",
        transport="vp8channel",
        connection_type="telemost",
        vp8_fps=60,
        vp8_batch=32,
    )

    command = SingleServerProcess(config, state).command()

    assert command[command.index("-client-id") + 1] == "srv-android-01"
    assert "%android-01$vpnrtc" in state.connection_uri
    assert "%srv-android-01$vpnrtc" not in state.connection_uri
    assert "dns=192.168.50.53%3A53" in state.connection_uri_with_dns("192.168.50.53:53")


def test_server_role_prefix_is_idempotent():
    assert SingleServerProcess._server_client_id("srv-android-01") == "srv-android-01"
