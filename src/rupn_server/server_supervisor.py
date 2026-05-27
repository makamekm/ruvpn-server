from __future__ import annotations

import signal
import subprocess
import threading
import time
from collections.abc import Iterable
from typing import NamedTuple

from rupn_server.config import ServerConfig
from rupn_server.server_state import ServerState
from rupn_server.single_server_process import SingleServerProcess
from rupn_server.vp8_log_stats import Vp8StatsSample, last_vp8_stats


class Vp8IngressHealth(NamedTuple):
    in_frames: int
    out_frames: int
    outbound_queue: int
    outbound_queue_cap: int
    frozen_since: float
    has_seen_ingress: bool
    has_peer_marker: bool
    outbound_advancing: bool


class Vp8IngressFailure(NamedTuple):
    reason: str
    in_frames: int
    out_frames: int
    frozen_for: float


class Vp8IngressMonitor:
    def __init__(self) -> None:
        self.health: Vp8IngressHealth | None = None
        self.failure: Vp8IngressFailure | None = None
        self.has_peer_marker = False
        self.has_fresh_signal = False

    def feed(self, line: str, now: float | None = None) -> None:
        if "vp8channel: peer first seen" in line or "vp8channel: KCP started" in line:
            self.has_peer_marker = True
            self.has_fresh_signal = True
        sample = last_vp8_stats(line)
        if sample is None:
            return
        self.feed_sample(sample, now=time.time() if now is None else now)

    def feed_sample(self, sample: Vp8StatsSample, now: float) -> None:
        self.has_fresh_signal = True
        previous = self.health
        has_seen_ingress = sample.in_frames > 0 or (previous.has_seen_ingress if previous is not None else False)
        has_peer_marker = self.has_peer_marker or (previous.has_peer_marker if previous is not None else False)
        if previous is None:
            self.health = Vp8IngressHealth(
                sample.in_frames,
                sample.out_frames,
                sample.outbound_queue,
                sample.outbound_queue_cap,
                now,
                has_seen_ingress,
                has_peer_marker,
                False,
            )
            self.failure = None
            return
        if sample.in_frames != previous.in_frames:
            self.health = Vp8IngressHealth(
                sample.in_frames,
                sample.out_frames,
                sample.outbound_queue,
                sample.outbound_queue_cap,
                now,
                has_seen_ingress,
                has_peer_marker,
                sample.out_frames > previous.out_frames,
            )
            self.failure = None
            return
        outbound_advancing = sample.out_frames > previous.out_frames
        frozen_since = previous.frozen_since if outbound_advancing else now
        self.health = Vp8IngressHealth(
            sample.in_frames,
            sample.out_frames,
            sample.outbound_queue,
            sample.outbound_queue_cap,
            frozen_since,
            has_seen_ingress,
            has_peer_marker,
            outbound_advancing,
        )
        self.failure = None

    def evaluate(self, *, frozen_after_seconds: float, zero_ingress_after_seconds: float, now: float | None = None) -> Vp8IngressFailure | None:
        if not self.has_fresh_signal:
            return None
        self.has_fresh_signal = False
        current = self.health
        if current is None:
            return None
        if current.out_frames <= 0 or not current.outbound_advancing:
            return None
        checked_at = time.time() if now is None else now
        frozen_for = checked_at - current.frozen_since
        if not current.has_seen_ingress:
            if zero_ingress_after_seconds > 0 and frozen_for >= zero_ingress_after_seconds and (current.has_peer_marker or self.has_peer_marker):
                self.failure = Vp8IngressFailure("zero ingress", current.in_frames, current.out_frames, frozen_for)
                return self.failure
            return None
        if frozen_after_seconds > 0 and frozen_for >= frozen_after_seconds:
            self.failure = Vp8IngressFailure("ingress frozen", current.in_frames, current.out_frames, frozen_for)
            return self.failure
        return None


class OlcRtcLogStatus:
    OK_MARKERS = (
        "Link connected",
        "telemost publisher state: connected",
        "telemost subscriber state: connected",
        "vp8channel: KCP started",
        "vp8channel stats:",
    )
    BAD_MARKERS = (
        "failed to connect link",
        "ws read error",
    )

    def __init__(self) -> None:
        self._last_status: str | None = None

    @property
    def is_bad(self) -> bool:
        return self._last_status == "bad"

    def feed(self, line: str) -> None:
        status = self.classify_line(line)
        if status is not None:
            self._last_status = status

    @classmethod
    def from_lines(cls, lines: Iterable[str]) -> "OlcRtcLogStatus":
        status = cls()
        for line in lines:
            status.feed(line)
        return status

    @classmethod
    def classify_line(cls, line: str) -> str | None:
        if any(marker in line for marker in cls.OK_MARKERS):
            return "ok"
        if any(marker in line for marker in cls.BAD_MARKERS):
            return "bad"
        return None


def should_restart_for_bad_status(
    *,
    bad_after_seconds: float,
    started_at: float,
    now: float,
    log_status: OlcRtcLogStatus,
) -> bool:
    if bad_after_seconds <= 0:
        return False
    if not log_status.is_bad:
        return False
    return now - started_at >= bad_after_seconds


def should_restart_for_vp8_ingress(
    *,
    frozen_after_seconds: float,
    zero_ingress_after_seconds: float,
    now: float,
    monitor: Vp8IngressMonitor,
) -> Vp8IngressFailure | None:
    return monitor.evaluate(
        frozen_after_seconds=frozen_after_seconds,
        zero_ingress_after_seconds=zero_ingress_after_seconds,
        now=now,
    )


class ServerSupervisor:
    def __init__(self, config: ServerConfig, state: ServerState) -> None:
        self.config = config
        self.state = state
        self.stopping = False
        self.process: subprocess.Popen[str] | None = None

    def run(self) -> int:
        signal.signal(signal.SIGTERM, self._terminate)
        signal.signal(signal.SIGINT, self._terminate)

        exit_code = 0
        while not self.stopping:
            exit_code = self._run_once()
            if self.stopping:
                return exit_code
            print(
                f"RUPN server process exited rc={exit_code}; restarting in {self.config.restart_backoff_seconds:.1f}s",
                flush=True,
            )
            time.sleep(self.config.restart_backoff_seconds)
        return exit_code

    def _run_once(self) -> int:
        log_status = OlcRtcLogStatus()
        vp8_monitor = Vp8IngressMonitor()
        started_at = time.time()
        self.process = SingleServerProcess(self.config, self.state).start(
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        reader = threading.Thread(target=self._read_output, args=(self.process, log_status, vp8_monitor), daemon=True)
        reader.start()

        while not self.stopping:
            assert self.process is not None
            return_code = self.process.poll()
            if return_code is not None:
                reader.join(timeout=1.0)
                return return_code
            now = time.time()
            if should_restart_for_bad_status(
                bad_after_seconds=self.config.bad_after_seconds,
                started_at=started_at,
                now=now,
                log_status=log_status,
            ):
                print("RUPN server bad log status; restarting olcrtc", flush=True)
                self._stop_process()
                reader.join(timeout=1.0)
                return 0
            vp8_failure = should_restart_for_vp8_ingress(
                frozen_after_seconds=self.config.vp8_ingress_frozen_after_seconds,
                zero_ingress_after_seconds=self.config.vp8_zero_ingress_after_seconds,
                now=now,
                monitor=vp8_monitor,
            )
            if vp8_failure is not None:
                print(
                    "RUPN server vp8 "
                    f"{vp8_failure.reason}; "
                    f"in_frames={vp8_failure.in_frames} "
                    f"out_frames={vp8_failure.out_frames} "
                    f"frozen_for={vp8_failure.frozen_for:.0f}s; restarting olcrtc",
                    flush=True,
                )
                self._stop_process()
                reader.join(timeout=1.0)
                return 0
            time.sleep(1.0)

        self._stop_process()
        reader.join(timeout=1.0)
        assert self.process is not None
        return self.process.returncode if self.process.returncode is not None else 0

    @staticmethod
    def _read_output(
        process: subprocess.Popen[str],
        log_status: OlcRtcLogStatus,
        vp8_monitor: Vp8IngressMonitor,
    ) -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            print(line, end="", flush=True)
            log_status.feed(line)
            vp8_monitor.feed(line)

    def _terminate(self, _signum: int, _frame: object) -> None:
        self.stopping = True
        self._stop_process()

    def _stop_process(self) -> None:
        process = self.process
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5.0)
