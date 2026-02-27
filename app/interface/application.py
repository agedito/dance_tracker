from typing import Protocol

from app.interface.media import MediaPort
from app.interface.sequence_data import SequenceDataPort
from app.interface.sequences import SequencePort
from app.interface.track_detector import TrackDetectorPort


class FramesPort(Protocol):
    fps: int
    total_frames: int
    layers: list
    error_frames: list[int]
    cur_frame: int
    playing: bool
    frame_cache_radius: int
    preload_anchor_points: int

    def set_frame(self, frame: int) -> int: ...

    def set_total_frames(self, total_frames: int) -> None: ...

    def play(self) -> None: ...

    def pause(self) -> None: ...

    def step(self, delta: int) -> int: ...

    def go_to_start(self) -> int: ...

    def go_to_end(self) -> int: ...

    def next_error_frame(self) -> int | None: ...

    def prev_error_frame(self) -> int | None: ...

    def advance_if_playing(self) -> bool: ...


class DanceTrackerPort(Protocol):
    media: MediaPort
    sequences: SequencePort
    frames: FramesPort
    sequence_data: SequenceDataPort
    track_detector: TrackDetectorPort
