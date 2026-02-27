from typing import Protocol

from app.interface.media import MediaPort
from app.interface.sequences import SequencePort


class DanceTrackerPort(Protocol):
    media: MediaPort
    sequences: SequencePort

# class PlaybackPort(Protocol):
#     def play(self) -> None: ...
#
#     def pause(self) -> None: ...
#
#     def set_frame(self, frame: int) -> None: ...


#
# TODO: define complete application contract if needed
# class DanceTrackerPort(Protocol):
#     """Contract that the UI expects from the application layer."""
#
#     @property
#     def fps(self) -> int: ...
#
#     @property
#     def cur_frame(self) -> int: ...
#
#     @property
#     def total_frames(self) -> int: ...
#
#     @property
#     def playing(self) -> bool: ...
#
#     @property
#     def error_frames(self) -> set[int]: ...
#
#     @property
#     def layers(self) -> list: ...
#
#     def set_frame(self, frame: int) -> None: ...
#
#     def set_total_frames(self, total: int) -> None: ...
#
#     def advance_if_playing(self) -> bool: ...
#
#     def next_error_frame(self) -> int | None: ...
#
#     def prev_error_frame(self) -> int | None: ...
#
#     def load_folder(self, path: str) -> int: ...
