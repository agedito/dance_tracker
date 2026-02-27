from typing import Callable

from PySide6.QtCore import QTimer

from app.interface.application import FramesPort


class PlaybackController:
    """Single responsibility: manage playback timing and frame navigation."""

    def __init__(self, fps: int, frames: FramesPort, on_frame_changed: Callable[[int], None]):
        self._frames = frames
        self._on_frame = on_frame_changed

        self._timer = QTimer()
        self._timer.setInterval(int(1000 / fps))
        self._timer.timeout.connect(self._tick)

    def play(self):
        if self._frames.playing:
            return
        self._frames.play()
        self._on_frame(self._frames.cur_frame)
        self._timer.start()

    def pause(self):
        self._frames.pause()
        self._timer.stop()
        self._on_frame(self._frames.cur_frame)

    def next_error(self):
        frame = self._frames.next_error_frame()
        if frame is not None:
            self._on_frame(frame)

    def prev_error(self):
        frame = self._frames.prev_error_frame()
        if frame is not None:
            self._on_frame(frame)

    def step(self, delta: int):
        self._on_frame(self._frames.step(delta))

    def go_to_start(self):
        self._on_frame(self._frames.go_to_start())

    def go_to_end(self):
        self._on_frame(self._frames.go_to_end())

    def stop(self):
        self._timer.stop()

    def _tick(self):
        advanced = self._frames.advance_if_playing()
        if not advanced and not self._frames.playing:
            self._timer.stop()
            return
        self._on_frame(self._frames.cur_frame)
