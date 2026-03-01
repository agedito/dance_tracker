import json
from dataclasses import asdict
from pathlib import Path

from app.interface.track_detector import BoundingBox, PersonDetection, RelativeBoundingBox


class DetectionsStore:
    """Single responsibility: read and write detections.json for a frames folder."""

    @staticmethod
    def json_path(frames_folder_path: str) -> Path:
        return Path(frames_folder_path).expanduser().parent / "detections.json"

    @staticmethod
    def write(
        frames_folder_path: str,
        detector_name: str,
        detections: dict[int, list[PersonDetection]],
    ) -> None:
        payload = {
            "detector": detector_name,
            "frames": {
                str(frame_index): [asdict(detection) for detection in frame_detections]
                for frame_index, frame_detections in detections.items()
            },
        }
        DetectionsStore.json_path(frames_folder_path).write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    @staticmethod
    def read(
        frames_folder_path: str,
    ) -> tuple[dict[int, list[PersonDetection]], str | None]:
        """Return (detections, saved_detector_name).

        saved_detector_name is None when the file is missing or has no detector key.
        No side effects — the caller decides whether to apply the detector name.
        """
        json_path = DetectionsStore.json_path(frames_folder_path)
        if not json_path.exists():
            return {}, None

        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}, None

        if not isinstance(payload, dict):
            return {}, None

        detector_name = payload.get("detector")
        saved_name = detector_name if isinstance(detector_name, str) else None

        frames_data = payload.get("frames")
        if not isinstance(frames_data, dict):
            return {}, saved_name

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

        return detections, saved_name


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
