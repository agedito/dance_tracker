from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PoseLandmark:
    index: int
    name: str
    x: float  # normalized 0-1 (image width)
    y: float  # normalized 0-1 (image height)
    z: float
    visibility: float


@dataclass(frozen=True)
class PoseDetection:
    landmarks: tuple[PoseLandmark, ...]


class PoseDetectorPort(Protocol):
    def set_active_provider(self, provider: str) -> bool: ...

    def detect_for_sequence(self, frames_folder_path: str, frame_index: int | None = None) -> int: ...

    def detect_for_video(self, frames_folder_path: str) -> int: ...

    def detect_streaming(
        self,
        frames_folder_path: str,
        should_cancel: Callable[[], bool] | None = None,
        current_frame: int = 0,
    ) -> int: ...

    def load_poses(self, frames_folder_path: str) -> None: ...

    def clear_poses(self, frames_folder_path: str) -> None: ...

    def poses_for_frame(self, frame_index: int) -> list[PoseDetection]: ...

    def detected_pose_flags(self, total_frames: int) -> list[bool]: ...
