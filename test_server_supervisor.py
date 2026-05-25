from rupn_server.server_supervisor import OlcRtcLogStatus, should_restart_for_bad_status


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
