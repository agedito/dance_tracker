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


def clamp(n: int, a: int, b: int) -> int:
    return max(a, min(b, n))


class ReviewState:
    def __init__(self, total_frames: int, fps: int, layers: List[Layer]):
        self.total_frames = total_frames
        self.fps = fps
        self.layers = layers
        self.error_frames = self._compute_error_frames()
        self.cur_frame = 0
        self.playing = False

    def set_frame(self, frame: int) -> int:
        self.cur_frame = clamp(frame, 0, self.total_frames - 1)
        return self.cur_frame

    def next_frame(self) -> int:
        return self.set_frame(self.cur_frame + 1)

    def prev_frame(self) -> int:
        return self.set_frame(self.cur_frame - 1)

    def next_error_frame(self):
        for frame in self.error_frames:
            if frame > self.cur_frame:
                return self.set_frame(frame)
        return None

    def prev_error_frame(self):
        for frame in reversed(self.error_frames):
            if frame < self.cur_frame:
                return self.set_frame(frame)
        return None

    def advance_if_playing(self) -> bool:
        if not self.playing:
            return False
        if self.cur_frame >= self.total_frames - 1:
            self.playing = False
            return False
        self.next_frame()
        return True

    def _compute_error_frames(self) -> List[int]:
        frames = set()
        for layer in self.layers:
            for seg in layer.segments:
                if seg.t == "err":
                    for frame in range(seg.a, seg.b):
                        frames.add(frame)
        return sorted(frames)


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
