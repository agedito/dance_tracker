"""
MPVision API Client
===================
Cliente tipado para la API REST de MPVision (detección de poses,
bounding boxes y segmentación con MediaPipe).

Usage:
    client = MPVisionClient("http://localhost:8000")

    # Health check
    ok = client.health()

    # Pose en una imagen
    response = client.pose(PoseRequest(image_path="foto.jpg"))
    for pose in response.poses:
        for lm in pose.landmarks:
            print(lm.name, lm.x, lm.y)

    # BBox con render desactivado
    response = client.bbox(BBoxRequest(image_path="foto.jpg"), render=False)

    # Segmentación
    response = client.segmentation(SegmentationRequest(image_path="foto.jpg", mode=SegMode.OVERLAY))

    # Batch de poses en una carpeta
    response = client.pose_batch(PoseBatchRequest(folder_path="frames/"))
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


# ─── Enums ────────────────────────────────────────────────────────────────────

class PoseModelName(str, Enum):
    HEAVY = "heavy"
    FULL = "full"
    LITE = "lite"


class BBoxModelName(str, Enum):
    LITE0 = "lite0"
    LITE2 = "lite2"


class SegModelName(str, Enum):
    SELFIE = "selfie"
    MULTICLASS = "multiclass"
    DEEPLAB = "deeplab"


class SegMode(str, Enum):
    MASK = "mask"
    OVERLAY = "overlay"
    CUTOUT = "cutout"
    BLUR = "blur"


# ─── Request models ───────────────────────────────────────────────────────────

@dataclass
class PoseRequest:
    """Detección de pose en una imagen."""
    image_path: str
    model_name: PoseModelName = PoseModelName.HEAVY
    num_poses: int = 5
    min_detection_confidence: float = 0.5

    def to_dict(self) -> dict:
        return {
            "image_path": self.image_path,
            "model_name": self.model_name.value,
            "num_poses": self.num_poses,
            "min_detection_confidence": self.min_detection_confidence,
        }


@dataclass
class PoseBatchRequest:
    """Detección de pose en todos los frames de una carpeta."""
    folder_path: str
    model_name: PoseModelName = PoseModelName.HEAVY
    num_poses: int = 5
    min_detection_confidence: float = 0.5

    def to_dict(self) -> dict:
        return {
            "folder_path": self.folder_path,
            "model_name": self.model_name.value,
            "num_poses": self.num_poses,
            "min_detection_confidence": self.min_detection_confidence,
        }


@dataclass
class BBoxRequest:
    """Detección de bounding boxes de personas en una imagen."""
    image_path: str
    model_name: BBoxModelName = BBoxModelName.LITE2
    score_threshold: float = 0.4
    max_results: int = 20

    def to_dict(self) -> dict:
        return {
            "image_path": self.image_path,
            "model_name": self.model_name.value,
            "score_threshold": self.score_threshold,
            "max_results": self.max_results,
        }


@dataclass
class BBoxBatchRequest:
    """Detección de bounding boxes en todos los frames de una carpeta."""
    folder_path: str
    model_name: BBoxModelName = BBoxModelName.LITE2
    score_threshold: float = 0.4
    max_results: int = 20

    def to_dict(self) -> dict:
        return {
            "folder_path": self.folder_path,
            "model_name": self.model_name.value,
            "score_threshold": self.score_threshold,
            "max_results": self.max_results,
        }


@dataclass
class SegmentationRequest:
    """Segmentación de personas en una imagen."""
    image_path: str
    model_name: SegModelName = SegModelName.SELFIE
    mode: SegMode = SegMode.MASK

    def to_dict(self) -> dict:
        return {
            "image_path": self.image_path,
            "model_name": self.model_name.value,
            "mode": self.mode.value,
        }


@dataclass
class SegBatchRequest:
    """Segmentación en todos los frames de una carpeta."""
    folder_path: str
    model_name: SegModelName = SegModelName.SELFIE
    mode: SegMode = SegMode.MASK

    def to_dict(self) -> dict:
        return {
            "folder_path": self.folder_path,
            "model_name": self.model_name.value,
            "mode": self.mode.value,
        }


# ─── Response models ──────────────────────────────────────────────────────────

@dataclass
class LandmarkResponse:
    index: int
    name: str
    x: float
    y: float
    z: float
    visibility: float

    @classmethod
    def from_dict(cls, d: dict) -> LandmarkResponse:
        return cls(**d)


@dataclass
class WorldLandmarkResponse:
    index: int
    name: str
    x: float
    y: float
    z: float

    @classmethod
    def from_dict(cls, d: dict) -> WorldLandmarkResponse:
        return cls(**d)


@dataclass
class PoseResponse:
    landmarks: list[LandmarkResponse]
    world_landmarks: list[WorldLandmarkResponse]

    @classmethod
    def from_dict(cls, d: dict) -> PoseResponse:
        return cls(
            landmarks=[LandmarkResponse.from_dict(lm) for lm in d["landmarks"]],
            world_landmarks=[WorldLandmarkResponse.from_dict(wlm) for wlm in d["world_landmarks"]],
        )


@dataclass
class PoseDetectionResponse:
    num_poses: int
    image_width: int
    image_height: int
    poses: list[PoseResponse]
    elapsed_ms: float
    output_path: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> PoseDetectionResponse:
        return cls(
            num_poses=d["num_poses"],
            image_width=d["image_width"],
            image_height=d["image_height"],
            poses=[PoseResponse.from_dict(p) for p in d["poses"]],
            elapsed_ms=d["elapsed_ms"],
            output_path=d.get("output_path"),
        )


@dataclass
class PersonBBoxResponse:
    x: int
    y: int
    width: int
    height: int
    score: float
    center_x: int
    center_y: int

    @classmethod
    def from_dict(cls, d: dict) -> PersonBBoxResponse:
        return cls(**d)


@dataclass
class BBoxDetectionResponse:
    num_persons: int
    image_width: int
    image_height: int
    persons: list[PersonBBoxResponse]
    elapsed_ms: float
    output_path: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> BBoxDetectionResponse:
        return cls(
            num_persons=d["num_persons"],
            image_width=d["image_width"],
            image_height=d["image_height"],
            persons=[PersonBBoxResponse.from_dict(p) for p in d["persons"]],
            elapsed_ms=d["elapsed_ms"],
            output_path=d.get("output_path"),
        )


@dataclass
class SegmentInfoResponse:
    category_id: int
    name: str
    pixel_count: int
    percentage: float

    @classmethod
    def from_dict(cls, d: dict) -> SegmentInfoResponse:
        return cls(**d)


@dataclass
class SegmentationResponse:
    model_name: str
    image_width: int
    image_height: int
    segments: list[SegmentInfoResponse]
    elapsed_ms: float
    output_path: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> SegmentationResponse:
        return cls(
            model_name=d["model_name"],
            image_width=d["image_width"],
            image_height=d["image_height"],
            segments=[SegmentInfoResponse.from_dict(s) for s in d["segments"]],
            elapsed_ms=d["elapsed_ms"],
            output_path=d.get("output_path"),
        )


@dataclass
class BatchFrameSummary:
    filename: str
    output_path: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> BatchFrameSummary:
        return cls(
            filename=d["filename"],
            output_path=d.get("output_path"),
            error=d.get("error"),
        )


@dataclass
class BatchResponse:
    folder: str
    model_name: str
    total_frames: int
    processed: int
    failed: int
    elapsed_ms: float
    json_path: str
    frames: list[BatchFrameSummary]

    @classmethod
    def from_dict(cls, d: dict) -> BatchResponse:
        return cls(
            folder=d["folder"],
            model_name=d["model_name"],
            total_frames=d["total_frames"],
            processed=d["processed"],
            failed=d["failed"],
            elapsed_ms=d["elapsed_ms"],
            json_path=d["json_path"],
            frames=[BatchFrameSummary.from_dict(f) for f in d["frames"]],
        )


# ─── Exceptions ───────────────────────────────────────────────────────────────

class MPVisionError(Exception):
    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")
