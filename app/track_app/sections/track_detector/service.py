import json
import random
import re
from dataclasses import asdict
from pathlib import Path

import cv2

from app.interface.track_detector import (
    BoundingBox,
    PersonDetection,
    PersonDetector,
    PoseDetection,
    PoseKeypoint,
    RelativeBoundingBox,
)

try:
    import mediapipe as mp
except ImportError:  # pragma: no cover - optional runtime dependency
    mp = None


class MockPersonDetector:
    def detect_people_in_frame(
        self,
        frame_path: str,
        previous_detections: list[PersonDetection] | None = None,
    ) -> list[PersonDetection]:
        _ = previous_detections
        width, height = _image_size(frame_path)
        rng = random.Random(frame_path)

        left_box = _random_box(
            rng=rng,
            width=width,
            height=height,
            min_x_ratio=0.05,
            max_x_ratio=0.35,
        )
        right_box = _random_box(
            rng=rng,
            width=width,
            height=height,
            min_x_ratio=0.55,
            max_x_ratio=0.85,
        )

        return [
            _to_detection(rng, left_box, width, height),
            _to_detection(rng, right_box, width, height),
        ]


class NearbyMockPersonDetector:
    def detect_people_in_frame(
        self,
        frame_path: str,
        previous_detections: list[PersonDetection] | None = None,
    ) -> list[PersonDetection]:
        width, height = _image_size(frame_path)
        rng = random.Random(frame_path)

        if not previous_detections:
            return MockPersonDetector().detect_people_in_frame(frame_path=frame_path)

        detections: list[PersonDetection] = []
        for prev in previous_detections:
            box = _jitter_box_from_previous(rng=rng, previous=prev.bbox_relative, width=width, height=height)
            detections.append(_to_detection(rng=rng, box=box, width=width, height=height))
        return detections


class PoseDetector:
    def detect_poses_in_frame(self, frame_path: str) -> list[PoseDetection]:
        raise NotImplementedError


class MediaPipePoseDetector(PoseDetector):
    def __init__(self, min_detection_confidence: float = 0.4, min_tracking_confidence: float = 0.4):
        self._min_detection_confidence = min_detection_confidence
        self._min_tracking_confidence = min_tracking_confidence

    def detect_poses_in_frame(self, frame_path: str) -> list[PoseDetection]:
        if mp is None:
            return []

        image_bgr = cv2.imread(frame_path)
        if image_bgr is None:
            return []

        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        pose_api = mp.solutions.pose
        with pose_api.Pose(
            static_image_mode=True,
            model_complexity=1,
            min_detection_confidence=self._min_detection_confidence,
            min_tracking_confidence=self._min_tracking_confidence,
        ) as pose:
            result = pose.process(image_rgb)

        if result.pose_landmarks is None:
            return []

        mapped_keypoints = _landmarks_to_coco17(result.pose_landmarks.landmark)
        if not mapped_keypoints:
            return []

        return [
            PoseDetection(
                keypoints=mapped_keypoints,
                source="MediaPipe Pose",
            )
        ]


class TrackDetectorService:
    _VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

    def __init__(
        self,
        detectors: dict[str, PersonDetector],
        default_detector_name: str,
        pose_detectors: dict[str, PoseDetector],
        default_pose_detector_name: str,
    ):
        self._detectors = dict(detectors)
        self._active_detector_name = default_detector_name if default_detector_name in self._detectors else next(iter(self._detectors), "")
        self._pose_detectors = dict(pose_detectors)
        self._active_pose_detector_name = (
            default_pose_detector_name if default_pose_detector_name in self._pose_detectors else next(iter(self._pose_detectors), "")
        )
        self._detections_by_frame: dict[int, list[PersonDetection]] = {}
        self._poses_by_frame: dict[int, list[PoseDetection]] = {}

    def available_detectors(self) -> list[str]:
        return list(self._detectors.keys())

    def active_detector(self) -> str:
        return self._active_detector_name

    def set_active_detector(self, detector_name: str) -> bool:
        if detector_name not in self._detectors:
            return False
        self._active_detector_name = detector_name
        return True

    def detect_people_for_sequence(self, frames_folder_path: str) -> int:
        detector = self._detectors.get(self._active_detector_name)
        if detector is None:
            self._detections_by_frame = {}
            self._write_json(frames_folder_path, {})
            return 0

        frame_files = self._frame_files(frames_folder_path)
        detections: dict[int, list[PersonDetection]] = {}
        previous_detections: list[PersonDetection] | None = None

        for index, frame_path in enumerate(frame_files):
            frame_detections = detector.detect_people_in_frame(
                frame_path=str(frame_path),
                previous_detections=previous_detections,
            )
            detections[index] = frame_detections
            previous_detections = frame_detections

        self._detections_by_frame = detections
        self._write_json(frames_folder_path, detections)
        return len(frame_files)

    def load_detections(self, frames_folder_path: str) -> None:
        payload = self._read_json(frames_folder_path)
        self._detections_by_frame = payload

    def detections_for_frame(self, frame_index: int) -> list[PersonDetection]:
        return list(self._detections_by_frame.get(frame_index, []))

    def available_pose_detectors(self) -> list[str]:
        return list(self._pose_detectors.keys())

    def active_pose_detector(self) -> str:
        return self._active_pose_detector_name

    def set_active_pose_detector(self, detector_name: str) -> bool:
        if detector_name not in self._pose_detectors:
            return False
        self._active_pose_detector_name = detector_name
        return True

    def detect_poses_for_sequence(self, frames_folder_path: str) -> int:
        detector = self._pose_detectors.get(self._active_pose_detector_name)
        if detector is None:
            self._poses_by_frame = {}
            self._write_poses_json(frames_folder_path, {})
            return 0

        frame_files = self._frame_files(frames_folder_path)
        poses: dict[int, list[PoseDetection]] = {}
        for index, frame_path in enumerate(frame_files):
            poses[index] = detector.detect_poses_in_frame(str(frame_path))

        self._poses_by_frame = poses
        self._write_poses_json(frames_folder_path, poses)
        return len(frame_files)

    def load_poses(self, frames_folder_path: str) -> None:
        self._poses_by_frame = self._read_poses_json(frames_folder_path)

    def poses_for_frame(self, frame_index: int) -> list[PoseDetection]:
        return list(self._poses_by_frame.get(frame_index, []))

    def _frame_files(self, frames_folder_path: str) -> list[Path]:
        folder = Path(frames_folder_path).expanduser()
        if not folder.is_dir():
            return []

        return [
            file
            for file in sorted(folder.iterdir(), key=_natural_sort_key)
            if file.is_file() and file.suffix.lower() in self._VALID_SUFFIXES
        ]

    def _json_path(self, frames_folder_path: str) -> Path:
        return Path(frames_folder_path).expanduser().parent / "detections.json"

    def _write_json(self, frames_folder_path: str, detections: dict[int, list[PersonDetection]]) -> None:
        payload = {
            "detector": self._active_detector_name,
            "frames": {
                str(frame_index): [asdict(detection) for detection in frame_detections]
                for frame_index, frame_detections in detections.items()
            }
        }
        json_path = self._json_path(frames_folder_path)
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _read_json(self, frames_folder_path: str) -> dict[int, list[PersonDetection]]:
        json_path = self._json_path(frames_folder_path)
        if not json_path.exists():
            return {}

        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

        frames_data = payload.get("frames") if isinstance(payload, dict) else None
        detector_name = payload.get("detector") if isinstance(payload, dict) else None
        if isinstance(detector_name, str) and detector_name in self._detectors:
            self._active_detector_name = detector_name
        if not isinstance(frames_data, dict):
            return {}

        detections: dict[int, list[PersonDetection]] = {}
        for frame_key, items in frames_data.items():
            if not isinstance(frame_key, str) or not frame_key.isdigit() or not isinstance(items, list):
                continue
            frame_index = int(frame_key)
            parsed: list[PersonDetection] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                parsed_detection = _from_dict(item)
                if parsed_detection is not None:
                    parsed.append(parsed_detection)
            detections[frame_index] = parsed
        return detections

    def _poses_json_path(self, frames_folder_path: str) -> Path:
        return Path(frames_folder_path).expanduser().parent / "poses.json"

    def _write_poses_json(self, frames_folder_path: str, poses_by_frame: dict[int, list[PoseDetection]]) -> None:
        payload = {
            "detector": self._active_pose_detector_name,
            "frames": {
                str(frame_index): [asdict(pose_detection) for pose_detection in frame_poses]
                for frame_index, frame_poses in poses_by_frame.items()
            },
        }
        self._poses_json_path(frames_folder_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _read_poses_json(self, frames_folder_path: str) -> dict[int, list[PoseDetection]]:
        json_path = self._poses_json_path(frames_folder_path)
        if not json_path.exists():
            return {}

        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

        frames_data = payload.get("frames") if isinstance(payload, dict) else None
        detector_name = payload.get("detector") if isinstance(payload, dict) else None
        if isinstance(detector_name, str) and detector_name in self._pose_detectors:
            self._active_pose_detector_name = detector_name
        if not isinstance(frames_data, dict):
            return {}

        poses: dict[int, list[PoseDetection]] = {}
        for frame_key, items in frames_data.items():
            if not isinstance(frame_key, str) or not frame_key.isdigit() or not isinstance(items, list):
                continue
            parsed: list[PoseDetection] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                parsed_detection = _pose_from_dict(item)
                if parsed_detection is not None:
                    parsed.append(parsed_detection)
            poses[int(frame_key)] = parsed
        return poses


def _pose_from_dict(data: dict) -> PoseDetection | None:
    keypoints_data = data.get("keypoints")
    source = data.get("source")
    if not isinstance(keypoints_data, list):
        return None
    if not isinstance(source, str):
        source = "Unknown"

    keypoints: list[PoseKeypoint] = []
    for item in keypoints_data:
        if not isinstance(item, dict):
            return None
        x = item.get("x")
        y = item.get("y")
        confidence = item.get("confidence")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)) or not isinstance(confidence, (int, float)):
            return None
        keypoints.append(PoseKeypoint(x=float(x), y=float(y), confidence=float(confidence)))

    return PoseDetection(keypoints=keypoints, source=source)


def _landmarks_to_coco17(landmarks) -> list[PoseKeypoint]:
    if mp is None:
        return []

    pose_landmark = mp.solutions.pose.PoseLandmark
    mapping = [
        pose_landmark.NOSE,
        pose_landmark.LEFT_EYE,
        pose_landmark.RIGHT_EYE,
        pose_landmark.LEFT_EAR,
        pose_landmark.RIGHT_EAR,
        pose_landmark.LEFT_SHOULDER,
        pose_landmark.RIGHT_SHOULDER,
        pose_landmark.LEFT_ELBOW,
        pose_landmark.RIGHT_ELBOW,
        pose_landmark.LEFT_WRIST,
        pose_landmark.RIGHT_WRIST,
        pose_landmark.LEFT_HIP,
        pose_landmark.RIGHT_HIP,
        pose_landmark.LEFT_KNEE,
        pose_landmark.RIGHT_KNEE,
        pose_landmark.LEFT_ANKLE,
        pose_landmark.RIGHT_ANKLE,
    ]

    keypoints: list[PoseKeypoint] = []
    for landmark_id in mapping:
        landmark = landmarks[landmark_id.value]
        keypoints.append(
            PoseKeypoint(
                x=float(landmark.x),
                y=float(landmark.y),
                confidence=float(landmark.visibility),
            )
        )
    return keypoints


def _from_dict(data: dict) -> PersonDetection | None:
    confidence = data.get("confidence")
    bbox_pixels = data.get("bbox_pixels")
    bbox_relative = data.get("bbox_relative")
    if not isinstance(confidence, (int, float)):
        return None
    if not isinstance(bbox_pixels, dict) or not isinstance(bbox_relative, dict):
        return None

    required = {"x", "y", "width", "height"}
    if any(key not in bbox_pixels for key in required) or any(key not in bbox_relative for key in required):
        return None

    try:
        return PersonDetection(
            confidence=float(confidence),
            bbox_pixels=BoundingBox(
                x=int(bbox_pixels["x"]),
                y=int(bbox_pixels["y"]),
                width=int(bbox_pixels["width"]),
                height=int(bbox_pixels["height"]),
            ),
            bbox_relative=RelativeBoundingBox(
                x=float(bbox_relative["x"]),
                y=float(bbox_relative["y"]),
                width=float(bbox_relative["width"]),
                height=float(bbox_relative["height"]),
            ),
        )
    except (TypeError, ValueError):
        return None


def _random_box(rng: random.Random, width: int, height: int, min_x_ratio: float, max_x_ratio: float) -> BoundingBox:
    box_width = max(20, int(width * rng.uniform(0.16, 0.28)))
    box_height = max(20, int(height * rng.uniform(0.30, 0.55)))
    max_x = max(0, int(width * max_x_ratio) - box_width)
    min_x = max(0, min(max_x, int(width * min_x_ratio)))
    x = rng.randint(min_x, max_x if max_x >= min_x else min_x)

    max_y = max(0, height - box_height)
    min_y = max(0, int(height * 0.05))
    y = rng.randint(min_y, max_y if max_y >= min_y else min_y)
    return BoundingBox(x=x, y=y, width=box_width, height=box_height)


def _jitter_box_from_previous(rng: random.Random, previous: RelativeBoundingBox, width: int, height: int) -> BoundingBox:
    prev_x = previous.x * width
    prev_y = previous.y * height
    prev_width = previous.width * width
    prev_height = previous.height * height

    new_width = max(20, int(prev_width * rng.uniform(0.92, 1.08)))
    new_height = max(20, int(prev_height * rng.uniform(0.92, 1.08)))

    x_shift = int(width * rng.uniform(-0.03, 0.03))
    y_shift = int(height * rng.uniform(-0.03, 0.03))

    x = int(prev_x) + x_shift
    y = int(prev_y) + y_shift

    x = max(0, min(x, max(0, width - new_width)))
    y = max(0, min(y, max(0, height - new_height)))
    return BoundingBox(x=x, y=y, width=new_width, height=new_height)


def _to_detection(rng: random.Random, box: BoundingBox, width: int, height: int) -> PersonDetection:
    return PersonDetection(
        confidence=round(rng.uniform(0.7, 0.99), 3),
        bbox_pixels=box,
        bbox_relative=RelativeBoundingBox(
            x=box.x / width,
            y=box.y / height,
            width=box.width / width,
            height=box.height / height,
        ),
    )


def _image_size(frame_path: str) -> tuple[int, int]:
    path = Path(frame_path)
    if not path.exists():
        return 1920, 1080

    try:
        with path.open("rb") as fh:
            header = fh.read(32)
            if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
                width = int.from_bytes(header[16:20], "big")
                height = int.from_bytes(header[20:24], "big")
                if width > 0 and height > 0:
                    return width, height

            if header.startswith(b"BM") and len(header) >= 26:
                fh.seek(18)
                dib = fh.read(8)
                width = int.from_bytes(dib[0:4], "little")
                height = int.from_bytes(dib[4:8], "little")
                if width > 0 and height > 0:
                    return width, abs(height)

            fh.seek(0)
            data = fh.read()
            jpeg_size = _jpeg_size(data)
            if jpeg_size is not None:
                return jpeg_size
    except OSError:
        return 1920, 1080

    return 1920, 1080


def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        return None

    idx = 2
    while idx + 9 < len(data):
        if data[idx] != 0xFF:
            idx += 1
            continue

        marker = data[idx + 1]
        idx += 2

        if marker in {0xD8, 0xD9}:
            continue

        if idx + 2 > len(data):
            return None

        segment_length = int.from_bytes(data[idx:idx + 2], "big")
        if segment_length < 2 or idx + segment_length > len(data):
            return None

        if marker in {0xC0, 0xC2}:
            if idx + 7 >= len(data):
                return None
            height = int.from_bytes(data[idx + 3:idx + 5], "big")
            width = int.from_bytes(data[idx + 5:idx + 7], "big")
            if width > 0 and height > 0:
                return width, height
            return None

        idx += segment_length

    return None


def _natural_sort_key(path: Path):
    chunks = re.split(r"(\d+)", path.name.lower())
    return [int(chunk) if chunk.isdigit() else chunk for chunk in chunks]
