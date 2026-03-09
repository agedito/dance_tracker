import re
from collections.abc import Callable
from pathlib import Path

from app.interface.segmentation import SegmentationResult
from app.track_app.sections.track_detector.segmentation_api_adapter import SegmentationApiAdapter
from app.track_app.sections.track_detector.segmentation_store import SegmentationStore
from app.track_app.sections.video_manager import sequence_file_store
from utils.frame_scheduler import FrameScheduler

_VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


class SegmentationService:
    def __init__(
        self,
        detectors: dict[str, SegmentationApiAdapter],
        default_provider: str = "",
        data_path: str = "",
    ):
        self._detectors = dict(detectors)
        self._active_provider = (
            default_provider
            if default_provider in self._detectors
            else next(iter(self._detectors), "")
        )
        self._data_path = data_path
        self._segmentations: dict[int, SegmentationResult] = {}

    def set_active_provider(self, provider: str) -> bool:
        if provider not in self._detectors:
            return False
        if self._active_provider != provider:
            self._active_provider = provider
            self._segmentations = {}
        return True

    def detect_for_sequence(self, frames_folder_path: str, frame_index: int | None = None) -> int:
        detector = self._detectors.get(self._active_provider)
        if detector is None:
            self._segmentations = {}
            SegmentationStore.write(frames_folder_path, self._active_provider, {}, self._data_path)
            return 0

        frame_files = self._frame_files(frames_folder_path)

        if frame_index is not None:
            if frame_index < 0 or frame_index >= len(frame_files):
                return 0
            result = detector.detect_in_frame(str(frame_files[frame_index]))
            segs = dict(self._segmentations)
            if result is not None:
                segs[frame_index] = result
            self._segmentations = segs
            SegmentationStore.write(frames_folder_path, self._active_provider, segs, self._data_path)
            return 1

        batch = detector.detect_in_batch(frames_folder_path)
        self._segmentations = {
            i: r for i, r in enumerate(batch) if r is not None
        }
        SegmentationStore.write(
            frames_folder_path, self._active_provider, self._segmentations, self._data_path
        )
        return len(self._segmentations)

    def detect_for_video(self, frames_folder_path: str) -> int:
        # Segmentation has no video endpoint — fall back to batch over the frames folder.
        return self.detect_for_sequence(frames_folder_path)

    def detect_streaming(
        self,
        frames_folder_path: str,
        on_frame_resolved: Callable[[int, SegmentationResult | None], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
        current_frame: int = 0,
    ) -> int:
        detector = self._detectors.get(self._active_provider)
        if detector is None:
            return 0

        saved, saved_provider = SegmentationStore.read(frames_folder_path, self._data_path)
        if saved_provider is None or saved_provider == self._active_provider:
            self._segmentations = dict(saved)
        else:
            self._segmentations = {}

        frame_files = self._frame_files(frames_folder_path)
        total = len(frame_files)
        if total == 0:
            return 0

        anchors = FrameScheduler.make_anchors(total, current_frame=current_frame)
        order = FrameScheduler.build_order(total, anchors)

        count = 0
        for index in order:
            if should_cancel and should_cancel():
                break
            result = detector.detect_in_frame(str(frame_files[index]))
            if result is not None:
                self._segmentations[index] = result
            count += 1
            if on_frame_resolved:
                on_frame_resolved(index, result)

        SegmentationStore.write(
            frames_folder_path, self._active_provider, self._segmentations, self._data_path
        )
        return count

    def load_segmentations(self, frames_folder_path: str) -> None:
        segs, saved_provider = SegmentationStore.read(frames_folder_path, self._data_path)
        self._segmentations = segs
        if saved_provider and saved_provider in self._detectors:
            self._active_provider = saved_provider

    def clear_segmentations(self, frames_folder_path: str) -> None:
        self._segmentations = {}
        SegmentationStore.write(frames_folder_path, self._active_provider, {}, self._data_path)

    def segmentation_for_frame(self, frame_index: int) -> SegmentationResult | None:
        return self._segmentations.get(frame_index)

    def detected_segmentation_flags(self, total_frames: int) -> list[bool]:
        return [frame_index in self._segmentations for frame_index in range(total_frames)]

    def _frame_files(self, frames_folder_path: str) -> list[Path]:
        folder = Path(frames_folder_path).expanduser()
        if not folder.is_dir():
            return []
        return [
            f for f in sorted(folder.iterdir(), key=_natural_sort_key)
            if f.is_file() and f.suffix.lower() in _VALID_SUFFIXES
        ]


def _natural_sort_key(path: Path):
    chunks = re.split(r"(\d+)", path.name.lower())
    return [int(c) if c.isdigit() else c for c in chunks]


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
