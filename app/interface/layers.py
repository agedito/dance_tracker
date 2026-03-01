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
