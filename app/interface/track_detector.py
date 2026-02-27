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


@dataclass(frozen=True)
class PoseKeypoint:
    x: float
    y: float
    confidence: float


@dataclass(frozen=True)
class PoseDetection:
    keypoints: list[PoseKeypoint]
    source: str


class PersonDetector(Protocol):
    def detect_people_in_frame(
        self,
        frame_path: str,
        previous_detections: list[PersonDetection] | None = None,
    ) -> list[PersonDetection]: ...


class TrackDetectorPort(Protocol):
    def available_detectors(self) -> list[str]: ...

    def active_detector(self) -> str: ...

    def set_active_detector(self, detector_name: str) -> bool: ...

    def detect_people_for_sequence(self, frames_folder_path: str) -> int: ...

    def load_detections(self, frames_folder_path: str) -> None: ...

    def detections_for_frame(self, frame_index: int) -> list[PersonDetection]: ...

    def available_pose_detectors(self) -> list[str]: ...

    def active_pose_detector(self) -> str: ...

    def set_active_pose_detector(self, detector_name: str) -> bool: ...

    def detect_poses_for_sequence(self, frames_folder_path: str) -> int: ...

    def load_poses(self, frames_folder_path: str) -> None: ...

    def poses_for_frame(self, frame_index: int) -> list[PoseDetection]: ...
