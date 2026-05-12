from __future__ import annotations

import signal
import subprocess


class ProcessWaiter:
    def __init__(self, process: subprocess.Popen[str]) -> None:
        self.process = process

    def wait(self) -> int:
        signal.signal(signal.SIGTERM, self._terminate)
        signal.signal(signal.SIGINT, self._terminate)
        return self.process.wait()

    def _terminate(self, _signum: int, _frame: object) -> None:
        if self.process.poll() is None:
            self.process.terminate()
