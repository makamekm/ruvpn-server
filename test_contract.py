from rupn_server.vp8_channel_options import Vp8ChannelOptions
from rupn_server.connection_type_registry import ConnectionTypeRegistry


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
