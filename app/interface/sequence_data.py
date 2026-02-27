from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SequenceVideoData:
    resolution_width: int
    resolution_height: int
    length_bytes: int
    duration_seconds: float
    frames: int
    fps: float


class SequenceDataPort(Protocol):
    def read_video_data(self, frames_folder_path: str) -> SequenceVideoData | None: ...

    def read_bookmarks(self, frames_folder_path: str) -> list[int]: ...

    def add_bookmark(self, frames_folder_path: str, frame: int) -> list[int]: ...

    def move_bookmark(self, frames_folder_path: str, source_frame: int, target_frame: int) -> list[int]: ...
