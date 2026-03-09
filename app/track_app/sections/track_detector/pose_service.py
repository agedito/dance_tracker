import re
from collections.abc import Callable
from pathlib import Path

from app.interface.pose_detector import PoseDetection
from app.track_app.sections.track_detector.pose_api_adapter import PoseApiDetector
from app.track_app.sections.track_detector.pose_store import PoseStore
from app.track_app.sections.video_manager import sequence_file_store
from utils.frame_scheduler import FrameScheduler

_VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


class PoseDetectorService:
    def __init__(self, detectors: dict[str, PoseApiDetector], default_provider: str = ""):
        self._detectors = dict(detectors)
        self._active_provider = (
            default_provider
            if default_provider in self._detectors
            else next(iter(self._detectors), "")
        )
        self._poses_by_frame: dict[int, list[PoseDetection]] = {}

    def set_active_provider(self, provider: str) -> bool:
        if provider not in self._detectors:
            return False
        if self._active_provider != provider:
            self._active_provider = provider
            self._poses_by_frame = {}
        return True

    def detect_for_sequence(self, frames_folder_path: str, frame_index: int | None = None) -> int:
        detector = self._detectors.get(self._active_provider)
        if detector is None:
            self._poses_by_frame = {}
            PoseStore.write(frames_folder_path, self._active_provider, {})
            return 0

        frame_files = self._frame_files(frames_folder_path)

        if frame_index is not None:
            if frame_index < 0 or frame_index >= len(frame_files):
                return 0
            poses = dict(self._poses_by_frame)
            poses[frame_index] = detector.detect_in_frame(str(frame_files[frame_index]))
            self._poses_by_frame = poses
            PoseStore.write(frames_folder_path, self._active_provider, poses)
            return 1

        if hasattr(detector, "detect_in_batch"):
            batch = detector.detect_in_batch(frames_folder_path)
            self._poses_by_frame = {i: r for i, r in enumerate(batch)}
        else:
            self._poses_by_frame = {}
            for i, f in enumerate(frame_files):
                self._poses_by_frame[i] = detector.detect_in_frame(str(f))

        PoseStore.write(frames_folder_path, self._active_provider, self._poses_by_frame)
        return len(self._poses_by_frame)

    def detect_for_video(self, frames_folder_path: str) -> int:
        detector = self._detectors.get(self._active_provider)
        if detector is None:
            return 0

        video_path = _find_video_path(frames_folder_path)
        if not video_path:
            return self.detect_for_sequence(frames_folder_path)

        results = detector.detect_in_video(video_path)
        self._poses_by_frame = {i: r for i, r in enumerate(results)}
        PoseStore.write(frames_folder_path, self._active_provider, self._poses_by_frame)
        return len(self._poses_by_frame)

    def detect_streaming(
        self,
        frames_folder_path: str,
        on_frame_resolved: Callable[[int, list[PoseDetection]], None],
        should_cancel: Callable[[], bool] | None = None,
        current_frame: int = 0,
    ) -> int:
        detector = self._detectors.get(self._active_provider)
        if detector is None:
            return 0

        saved, saved_provider = PoseStore.read(frames_folder_path)
        if saved_provider is None or saved_provider == self._active_provider:
            self._poses_by_frame = dict(saved)
        else:
            self._poses_by_frame = {}

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
            frame_poses = detector.detect_in_frame(str(frame_files[index]))
            self._poses_by_frame[index] = frame_poses
            count += 1
            on_frame_resolved(index, frame_poses)

        PoseStore.write(frames_folder_path, self._active_provider, self._poses_by_frame)
        return count

    def load_poses(self, frames_folder_path: str) -> None:
        poses, saved_provider = PoseStore.read(frames_folder_path)
        self._poses_by_frame = poses
        if saved_provider and saved_provider in self._detectors:
            self._active_provider = saved_provider

    def clear_poses(self, frames_folder_path: str) -> None:
        self._poses_by_frame = {}
        PoseStore.write(frames_folder_path, self._active_provider, {})

    def poses_for_frame(self, frame_index: int) -> list[PoseDetection]:
        return list(self._poses_by_frame.get(frame_index, []))

    def detected_pose_flags(self, total_frames: int) -> list[bool]:
        return [bool(self._poses_by_frame.get(i)) for i in range(total_frames)]

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
