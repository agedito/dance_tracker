from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class BoundingBox:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class RelativeBoundingBox:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class PersonDetection:
    confidence: float
    bbox_pixels: BoundingBox
    bbox_relative: RelativeBoundingBox


class PersonDetector(Protocol):
    def detect_people_in_frame(self, frame_path: str) -> list[PersonDetection]: ...


class TrackDetectorPort(Protocol):
    def detect_people_for_sequence(self, frames_folder_path: str) -> int: ...

    def load_detections(self, frames_folder_path: str) -> None: ...

    def detections_for_frame(self, frame_index: int) -> list[PersonDetection]: ...

