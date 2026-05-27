from rupn_server.server_supervisor import (
    OlcRtcLogStatus,
    Vp8IngressMonitor,
    should_restart_for_bad_status,
    should_restart_for_vp8_ingress,
)
from rupn_server.vp8_log_stats import parse_vp8_stats


def test_bad_after_zero_disables_bad_marker_restart():
    status = OlcRtcLogStatus.from_lines([
        "2026/05/25 16:13:38 vp8channel stats: out_frames=217330 out_bytes=1 in_frames=78726 in_bytes=1 outbound_queue=0/4096\n",
        "2026/05/25 16:13:40 ws read error: websocket: close 4009\n",
    ])

    assert should_restart_for_bad_status(
        bad_after_seconds=0,
        started_at=0,
        now=3600,
        log_status=status,
    ) is False


def test_telemost_closed_marker_alone_is_not_bad_status():
    status = OlcRtcLogStatus.from_lines([
        "2026/05/25 16:13:38 vp8channel stats: out_frames=217330 out_bytes=1 in_frames=78726 in_bytes=1 outbound_queue=0/4096\n",
        "2026/05/25 16:13:40 telemost publisher state: closed\n",
        "2026/05/25 16:13:40 telemost subscriber state: closed\n",
    ])

    assert status.is_bad is False
    assert should_restart_for_bad_status(
        bad_after_seconds=1,
        started_at=0,
        now=3600,
        log_status=status,
    ) is False


def test_ws_read_error_can_restart_when_watchdog_enabled():
    status = OlcRtcLogStatus.from_lines([
        "2026/05/25 16:13:38 vp8channel stats: out_frames=217330 out_bytes=1 in_frames=78726 in_bytes=1 outbound_queue=0/4096\n",
        "2026/05/25 16:13:40 ws read error: websocket: close 4009\n",
    ])

    assert should_restart_for_bad_status(
        bad_after_seconds=1,
        started_at=0,
        now=3600,
        log_status=status,
    ) is True


def _sample(out_frames: int, in_frames: int):
    return parse_vp8_stats(
        "2026/05/27 22:38:00 vp8channel stats: "
        f"out_frames={out_frames} out_bytes=1 "
        f"in_frames={in_frames} in_bytes=1 outbound_queue=0/4096"
    )[0]


def test_vp8_ingress_watchdogs_are_disabled_by_default():
    monitor = Vp8IngressMonitor()
    monitor.feed_sample(_sample(out_frames=10, in_frames=5), now=0)
    monitor.feed_sample(_sample(out_frames=500, in_frames=5), now=120)

    assert should_restart_for_vp8_ingress(
        frozen_after_seconds=0,
        zero_ingress_after_seconds=0,
        now=120,
        monitor=monitor,
    ) is None


def test_vp8_ingress_freeze_can_restart_when_explicitly_enabled():
    monitor = Vp8IngressMonitor()
    monitor.feed_sample(_sample(out_frames=10, in_frames=5), now=0)
    monitor.feed_sample(_sample(out_frames=500, in_frames=5), now=120)

    failure = should_restart_for_vp8_ingress(
        frozen_after_seconds=90,
        zero_ingress_after_seconds=0,
        now=120,
        monitor=monitor,
    )

    assert failure is not None
    assert failure.reason == "ingress frozen"
    assert failure.in_frames == 5
    assert failure.out_frames == 500


def test_vp8_zero_ingress_requires_peer_marker_before_restart():
    monitor = Vp8IngressMonitor()
    monitor.feed_sample(_sample(out_frames=10, in_frames=0), now=0)
    monitor.feed_sample(_sample(out_frames=500, in_frames=0), now=120)

    assert should_restart_for_vp8_ingress(
        frozen_after_seconds=0,
        zero_ingress_after_seconds=90,
        now=120,
        monitor=monitor,
    ) is None

    monitor.feed("2026/05/27 22:38:01 vp8channel: KCP started localEpoch=0x1234")
    failure = should_restart_for_vp8_ingress(
        frozen_after_seconds=0,
        zero_ingress_after_seconds=90,
        now=120,
        monitor=monitor,
    )

    assert failure is not None
    assert failure.reason == "zero ingress"
    assert failure.in_frames == 0
    assert failure.out_frames == 500


def test_vp8_ingress_progress_resets_freeze_timer():
    monitor = Vp8IngressMonitor()
    monitor.feed_sample(_sample(out_frames=10, in_frames=5), now=0)
    monitor.feed_sample(_sample(out_frames=500, in_frames=6), now=120)

    assert should_restart_for_vp8_ingress(
        frozen_after_seconds=90,
        zero_ingress_after_seconds=0,
        now=121,
        monitor=monitor,
    ) is None


def test_vp8_watchdog_does_not_restart_without_fresh_stats():
    monitor = Vp8IngressMonitor()
    monitor.feed_sample(_sample(out_frames=10, in_frames=5), now=0)
    monitor.feed_sample(_sample(out_frames=500, in_frames=5), now=10)

    assert should_restart_for_vp8_ingress(
        frozen_after_seconds=90,
        zero_ingress_after_seconds=0,
        now=10,
        monitor=monitor,
    ) is None
    assert should_restart_for_vp8_ingress(
        frozen_after_seconds=90,
        zero_ingress_after_seconds=0,
        now=120,
        monitor=monitor,
    ) is None
