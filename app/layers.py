from dataclasses import dataclass
from enum import Enum
from typing import List


class ResultState(str, Enum):
    Disabeld = "Disabeld"
    ok = "ok"
    Warning = "Warning"
    Error = "Error"


def result_state_color(state: ResultState) -> str:
    if state == ResultState.ok:
        return "verde"
    if state == ResultState.Warning:
        return "amarillo"
    if state == ResultState.Error:
        return "rojo"
    return "gris"


@dataclass(frozen=True)
class Segment:
    a: int
    b: int
    t: ResultState


@dataclass(frozen=True)
class Layer:
    name: str
    segments: List[Segment]


def default_layers() -> List[Layer]:
    return [
        Layer("Layer 0: Master Video", [
            Segment(0, 220, ResultState.ok), Segment(220, 420, ResultState.Warning), Segment(420, 520, ResultState.ok),
            Segment(520, 560, ResultState.Error), Segment(560, 980, ResultState.Warning), Segment(980, 1200, ResultState.ok),
        ]),
        Layer("Layer 1: Color Grade", [
            Segment(0, 120, ResultState.ok), Segment(120, 240, ResultState.Warning), Segment(240, 760, ResultState.ok),
            Segment(760, 820, ResultState.Error), Segment(820, 1200, ResultState.ok),
        ]),
        Layer("Layer 2: Object Mask", [
            Segment(0, 430, ResultState.ok), Segment(430, 470, ResultState.Error), Segment(470, 900, ResultState.ok),
            Segment(900, 980, ResultState.Warning), Segment(980, 1200, ResultState.ok),
        ]),
    ]
