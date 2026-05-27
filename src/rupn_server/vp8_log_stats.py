from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Vp8StatsSample:
    timestamp: str
    out_frames: int
    in_frames: int
    outbound_queue: int
    outbound_queue_cap: int


_STATS_RE = re.compile(
    r"(?P<timestamp>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*?"
    r"vp8channel stats: out_frames=(?P<out_frames>\d+).*?"
    r"in_frames=(?P<in_frames>\d+).*?"
    r"outbound_queue=(?P<outbound_queue>\d+)/(?P<outbound_queue_cap>\d+)"
)


def parse_vp8_stats(text: str) -> tuple[Vp8StatsSample, ...]:
    return tuple(
        Vp8StatsSample(
            timestamp=match.group("timestamp"),
            out_frames=int(match.group("out_frames")),
            in_frames=int(match.group("in_frames")),
            outbound_queue=int(match.group("outbound_queue")),
            outbound_queue_cap=int(match.group("outbound_queue_cap")),
        )
        for match in _STATS_RE.finditer(text)
    )


def last_vp8_stats(text: str) -> Vp8StatsSample | None:
    latest: Vp8StatsSample | None = None
    for sample in parse_vp8_stats(text):
        latest = sample
    return latest


def ingress_is_current(samples: Sequence[Vp8StatsSample], lookback_samples: int = 6) -> bool:
    if not samples:
        return False
    latest = samples[-1]
    if latest.in_frames <= 0:
        return False
    previous_samples = samples[max(0, len(samples) - 1 - lookback_samples) : -1]
    if not previous_samples:
        return True
    return any(latest.in_frames > sample.in_frames for sample in previous_samples)
