from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SegmentInfo:
    category_id: int
    name: str
    pixel_count: int
    percentage: float


@dataclass(frozen=True)
class SegmentationResult:
    mask_path: str | None          # absolute path to saved PNG mask; None if not available
    segments: tuple[SegmentInfo, ...]


class SegmentationPort(Protocol):
    def set_active_provider(self, provider: str) -> bool: ...

    def detect_for_sequence(self, frames_folder_path: str, frame_index: int | None = None) -> int: ...

    def detect_for_video(self, frames_folder_path: str) -> int: ...

    def detect_streaming(
        self,
        frames_folder_path: str,
        should_cancel: Callable[[], bool] | None = None,
        current_frame: int = 0,
    ) -> int: ...

    def load_segmentations(self, frames_folder_path: str) -> None: ...

    def clear_segmentations(self, frames_folder_path: str) -> None: ...

    def segmentation_for_frame(self, frame_index: int) -> SegmentationResult | None: ...

    def detected_segmentation_flags(self, total_frames: int) -> list[bool]: ...
