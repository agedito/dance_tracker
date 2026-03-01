from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SequenceItem:
    folder_path: str


@dataclass(frozen=True)
class SequenceState:
    items: list[SequenceItem]
    active_folder: str | None


class SequencePort(Protocol):
    def refresh(self) -> None: ...

    def load(self, folder_path: str) -> None: ...

    def move(self, dragged_folder: str, target_folder: str, drop_after: bool) -> None: ...

    def remove(self, folder_path: str) -> None: ...

    def delete_video_and_frames(self, folder_path: str) -> None: ...

    def last_opened_folder(self) -> str | None: ...

    def thumbnail_path_for_folder(self, folder_path: str) -> str | None: ...
