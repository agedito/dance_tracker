from typing import List

from app.layers import Layer
from utils.numbers import clamp


class ReviewState:
    def __init__(self, total_frames: int, fps: int, layers: List[Layer]):
        self.total_frames = total_frames
        self.fps = fps
        self.layers = layers
        self.error_frames = self._compute_error_frames()
        self.cur_frame = 0
        self.playing = False

    def set_frame(self, frame: int) -> int:
        self.cur_frame = clamp(frame, 0, max(0, self.total_frames - 1))
        return self.cur_frame

    def set_total_frames(self, total_frames: int):
        self.total_frames = max(1, total_frames)
        self.error_frames = [frame for frame in self.error_frames if frame < self.total_frames]
        self.set_frame(self.cur_frame)

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
