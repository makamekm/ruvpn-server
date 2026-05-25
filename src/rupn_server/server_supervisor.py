from __future__ import annotations

import signal
import subprocess
import threading
import time
from collections.abc import Iterable

from rupn_server.config import ServerConfig
from rupn_server.server_state import ServerState
from rupn_server.single_server_process import SingleServerProcess


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
        started_at = time.time()
        self.process = SingleServerProcess(self.config, self.state).start(
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        reader = threading.Thread(target=self._read_output, args=(self.process, log_status), daemon=True)
        reader.start()

        while not self.stopping:
            assert self.process is not None
            return_code = self.process.poll()
            if return_code is not None:
                reader.join(timeout=1.0)
                return return_code
            if should_restart_for_bad_status(
                bad_after_seconds=self.config.bad_after_seconds,
                started_at=started_at,
                now=time.time(),
                log_status=log_status,
            ):
                print("RUPN server bad log status; restarting olcrtc", flush=True)
                self._stop_process()
                reader.join(timeout=1.0)
                return 0
            time.sleep(1.0)

        self._stop_process()
        reader.join(timeout=1.0)
        assert self.process is not None
        return self.process.returncode if self.process.returncode is not None else 0

    @staticmethod
    def _read_output(process: subprocess.Popen[str], log_status: OlcRtcLogStatus) -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            print(line, end="", flush=True)
            log_status.feed(line)

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
