from typing import Callable, Protocol

from PySide6.QtCore import QTimer


class PlaybackState(Protocol):
    """Protocol for the state object the controller needs."""
    playing: bool
    cur_frame: int
    total_frames: int
    def advance_if_playing(self) -> bool: ...
    def next_error_frame(self) -> int | None: ...
    def prev_error_frame(self) -> int | None: ...


class PlaybackController:
    """Single responsibility: manage playback timing and frame navigation."""

    def __init__(self, fps: int, state: PlaybackState, on_frame_changed: Callable[[int], None]):
        self._state = state
        self._on_frame = on_frame_changed

        self._timer = QTimer()
        self._timer.setInterval(int(1000 / fps))
        self._timer.timeout.connect(self._tick)

    def play(self):
        if self._state.playing:
            return
        self._state.playing = True
        self._on_frame(self._state.cur_frame)
        self._timer.start()

    def pause(self):
        self._state.playing = False
        self._timer.stop()
        self._on_frame(self._state.cur_frame)

    def next_error(self):
        frame = self._state.next_error_frame()
        if frame is not None:
            self._on_frame(frame)

    def prev_error(self):
        frame = self._state.prev_error_frame()
        if frame is not None:
            self._on_frame(frame)

    def step(self, delta: int):
        self._on_frame(self._state.cur_frame + delta)

    def go_to_start(self):
        self._on_frame(0)

    def go_to_end(self):
        self._on_frame(max(0, self._state.total_frames - 1))

    def stop(self):
        self._timer.stop()

    def _tick(self):
        advanced = self._state.advance_if_playing()
        if not advanced and not self._state.playing:
            self._timer.stop()
            return
        self._on_frame(self._state.cur_frame)
