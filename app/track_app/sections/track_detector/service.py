import re
from pathlib import Path

from app.interface.track_detector import PersonDetection, PersonDetector
from app.track_app.sections.track_detector.detections_store import DetectionsStore


class TrackDetectorService:
    _VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

    def __init__(self, detectors: dict[str, PersonDetector], default_detector_name: str):
        self._detectors = dict(detectors)
        self._active_detector_name = (
            default_detector_name
            if default_detector_name in self._detectors
            else next(iter(self._detectors), "")
        )
        self._detections_by_frame: dict[int, list[PersonDetection]] = {}
        self._store = DetectionsStore()

    def available_detectors(self) -> list[str]:
        return list(self._detectors.keys())

    def active_detector(self) -> str:
        return self._active_detector_name

    def set_active_detector(self, detector_name: str) -> bool:
        if detector_name not in self._detectors:
            return False
        self._active_detector_name = detector_name
        return True

    def detect_people_for_sequence(self, frames_folder_path: str, frame_index: int | None = None) -> int:
        detector = self._detectors.get(self._active_detector_name)
        if detector is None:
            self._detections_by_frame = {}
            DetectionsStore.write(frames_folder_path, self._active_detector_name, {})
            return 0

        frame_files = self._frame_files(frames_folder_path)
        if frame_index is not None:
            if frame_index < 0 or frame_index >= len(frame_files):
                return 0

            detections = dict(self._detections_by_frame)
            if not detections:
                detections, _ = DetectionsStore.read(frames_folder_path)

            previous_detections = detections.get(frame_index - 1)
            frame_detections = detector.detect_people_in_frame(
                frame_path=str(frame_files[frame_index]),
                previous_detections=previous_detections,
            )
            detections[frame_index] = frame_detections
            self._detections_by_frame = detections
            DetectionsStore.write(frames_folder_path, self._active_detector_name, detections)
            return 1

        if hasattr(detector, "detect_people_in_batch"):
            batch_results = detector.detect_people_in_batch(frames_folder_path)
            detections = {i: r for i, r in enumerate(batch_results)}
        else:
            detections = {}
            previous_detections: list[PersonDetection] | None = None
            for index, frame_path in enumerate(frame_files):
                frame_detections = detector.detect_people_in_frame(
                    frame_path=str(frame_path),
                    previous_detections=previous_detections,
                )
                detections[index] = frame_detections
                previous_detections = frame_detections

        self._detections_by_frame = detections
        DetectionsStore.write(frames_folder_path, self._active_detector_name, detections)
        return len(frame_files)

    def load_detections(self, frames_folder_path: str) -> None:
        detections, saved_name = DetectionsStore.read(frames_folder_path)
        self._detections_by_frame = detections
        if saved_name is not None and saved_name in self._detectors:
            self._active_detector_name = saved_name

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


def _natural_sort_key(path: Path):
    chunks = re.split(r"(\d+)", path.name.lower())
    return [int(chunk) if chunk.isdigit() else chunk for chunk in chunks]
