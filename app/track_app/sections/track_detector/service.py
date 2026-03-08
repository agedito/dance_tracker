import logging
import re
from collections.abc import Callable
from pathlib import Path

from app.interface.track_detector import PersonDetection, PersonDetector
from app.track_app.sections.track_detector.detections_store import DetectionsStore
from app.track_app.sections.video_manager import sequence_file_store

log = logging.getLogger(__name__)


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
        self._detections_by_frame = {}
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
                file_detections, saved_name = DetectionsStore.read(frames_folder_path)
                if saved_name is None or saved_name == self._active_detector_name:
                    detections = file_detections

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
            image_size = _read_video_dimensions(frames_folder_path)
            batch_results = detector.detect_people_in_batch(frames_folder_path, image_size=image_size)
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
        return len(detections)

    def detect_people_for_video(self, frames_folder_path: str) -> int:
        detector = self._detectors.get(self._active_detector_name)
        if detector is None:
            return 0

        if not hasattr(detector, "detect_people_in_video"):
            return self.detect_people_for_sequence(frames_folder_path)

        video_path = _find_video_path(frames_folder_path)
        if not video_path:
            return self.detect_people_for_sequence(frames_folder_path)

        image_size = _read_video_dimensions(frames_folder_path)
        batch_results = detector.detect_people_in_video(video_path, image_size=image_size)
        detections = {i: r for i, r in enumerate(batch_results)}
        non_empty = sum(1 for v in detections.values() if v)
        self._detections_by_frame = detections
        DetectionsStore.write(frames_folder_path, self._active_detector_name, detections)
        return len(detections)

    def load_detections(self, frames_folder_path: str) -> None:
        detections, saved_name = DetectionsStore.read(frames_folder_path)
        self._detections_by_frame = detections
        if saved_name is not None and saved_name in self._detectors:
            self._active_detector_name = saved_name

    def detect_people_streaming(
        self,
        frames_folder_path: str,
        on_frame_resolved: Callable[[int, list[PersonDetection]], None],
        should_cancel: Callable[[], bool] | None = None,
    ) -> int:
        """Detect frame-by-frame via single-frame endpoint, calling on_frame_resolved after each.

        Loads existing detections from disk first so the in-memory state is up to date.
        Writes the full detections.json only when the loop finishes (or is cancelled).
        """
        detector = self._detectors.get(self._active_detector_name)
        if detector is None:
            return 0

        saved_detections, saved_name = DetectionsStore.read(frames_folder_path)
        if saved_name is None or saved_name == self._active_detector_name:
            self._detections_by_frame = dict(saved_detections)
        else:
            self._detections_by_frame = {}

        frame_files = self._frame_files(frames_folder_path)
        previous_detections: list[PersonDetection] | None = None
        resolved_count = 0

        for index, frame_path in enumerate(frame_files):
            if should_cancel and should_cancel():
                break

            frame_detections = detector.detect_people_in_frame(
                frame_path=str(frame_path),
                previous_detections=previous_detections,
            )
            self._detections_by_frame[index] = frame_detections
            previous_detections = frame_detections
            resolved_count += 1
            on_frame_resolved(index, frame_detections)

        DetectionsStore.write(frames_folder_path, self._active_detector_name, self._detections_by_frame)
        return resolved_count

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


def _read_video_dimensions(frames_folder_path: str) -> tuple[int, int]:
    folder = Path(frames_folder_path).expanduser()
    metadata_path = sequence_file_store.find_metadata_for_frames(folder)
    if not metadata_path:
        return (0, 0)
    metadata = sequence_file_store.read(metadata_path)
    if not metadata:
        return (0, 0)
    resolution = metadata.get("video", {}).get("data", {}).get("resolution", {})
    return (int(resolution.get("width", 0)), int(resolution.get("height", 0)))


def _find_video_path(frames_folder_path: str) -> str | None:
    folder = Path(frames_folder_path).expanduser()
    metadata_path = sequence_file_store.find_metadata_for_frames(folder)
    if not metadata_path:
        return None
    metadata = sequence_file_store.read(metadata_path)
    if not metadata:
        return None
    video_name = sequence_file_store.video_path_from_metadata(metadata)
    if not video_name:
        return None
    video_file = metadata_path.parent / video_name
    return str(video_file) if video_file.exists() else None
