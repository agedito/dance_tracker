from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Segment:
    a: int
    b: int
    t: str  # "ok" | "warn" | "err"


@dataclass(frozen=True)
class Layer:
    name: str
    segments: List[Segment]


def default_layers() -> List[Layer]:
    return [
        Layer("Layer 0: Master Video", [
            Segment(0, 220, "ok"), Segment(220, 420, "warn"), Segment(420, 520, "ok"),
            Segment(520, 560, "err"), Segment(560, 980, "warn"), Segment(980, 1200, "ok"),
        ]),
        Layer("Layer 1: Color Grade", [
            Segment(0, 120, "ok"), Segment(120, 240, "warn"), Segment(240, 760, "ok"),
            Segment(760, 820, "err"), Segment(820, 1200, "ok"),
        ]),
        Layer("Layer 2: Object Mask", [
            Segment(0, 430, "ok"), Segment(430, 470, "err"), Segment(470, 900, "ok"),
            Segment(900, 980, "warn"), Segment(980, 1200, "ok"),
        ]),
    ]
