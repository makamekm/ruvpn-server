from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Vp8ChannelOptions:
    fps: int
    batch: int

    @staticmethod
    def defaults() -> "Vp8ChannelOptions":
        return Vp8ChannelOptions(fps=60, batch=64)

    @staticmethod
    def bounded(fps: int, batch: int) -> "Vp8ChannelOptions":
        return Vp8ChannelOptions(
            fps=max(1, min(120, fps)),
            batch=max(1, min(64, batch)),
        )

    @property
    def transport_suffix(self) -> str:
        return f"vp8channel<vp8-fps={self.fps}&vp8-batch={self.batch}>"
