import json
import random
import re
from dataclasses import asdict
from pathlib import Path

from app.interface.track_detector import BoundingBox, PersonDetection, PersonDetector, RelativeBoundingBox


class MockPersonDetector:
    def detect_people_in_frame(self, frame_path: str) -> list[PersonDetection]:
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


class TrackDetectorService:
    _VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

    def __init__(self, detector: PersonDetector):
        self._detector = detector
        self._detections_by_frame: dict[int, list[PersonDetection]] = {}

    def detect_people_for_sequence(self, frames_folder_path: str) -> int:
        frame_files = self._frame_files(frames_folder_path)
        detections: dict[int, list[PersonDetection]] = {}

        for index, frame_path in enumerate(frame_files):
            detections[index] = self._detector.detect_people_in_frame(str(frame_path))

        self._detections_by_frame = detections
        self._write_json(frames_folder_path, detections)
        return len(frame_files)

    def load_detections(self, frames_folder_path: str) -> None:
        payload = self._read_json(frames_folder_path)
        self._detections_by_frame = payload

    def detections_for_frame(self, frame_index: int) -> list[PersonDetection]:
        return list(self._detections_by_frame.get(frame_index, []))

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
