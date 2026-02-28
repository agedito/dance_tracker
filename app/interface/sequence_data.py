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
    dance_style: str
    song: str
    follower: str
    leader: str
    event: str
    year: str


@dataclass(frozen=True)
class Bookmark:
    frame: int
    name: str = ""
    locked: bool = False


class SequenceDataPort(Protocol):
    def read_video_data(self, frames_folder_path: str) -> SequenceVideoData | None: ...

    def read_bookmarks(self, frames_folder_path: str) -> list[Bookmark]: ...

    def add_bookmark(self, frames_folder_path: str, frame: int) -> list[Bookmark]: ...

    def move_bookmark(self, frames_folder_path: str, source_frame: int, target_frame: int) -> list[Bookmark]: ...

    def remove_bookmark(self, frames_folder_path: str, frame: int) -> list[Bookmark]: ...

    def set_bookmark_name(self, frames_folder_path: str, frame: int, name: str) -> list[Bookmark]: ...

    def set_bookmark_locked(self, frames_folder_path: str, frame: int, locked: bool) -> list[Bookmark]: ...
