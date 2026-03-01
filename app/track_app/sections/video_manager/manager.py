import shutil
from collections.abc import Callable
from pathlib import Path

import cv2

VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}
VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


class VideoManager:
    """Single responsibility: validate video files and extract frames to disk.

    Metadata I/O (.dance_tracker.json) is handled by SequenceMetadataStore.
    """

    @staticmethod
    def is_video(video_path: str) -> bool:
        source = Path(video_path)
        return source.exists() and source.is_file() and source.suffix.lower() in VIDEO_SUFFIXES

    def extract_frames(
        self,
        video_path: str,
        on_progress: Callable[[int], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> tuple[str, dict] | None:
        """Extract full-size and 320px proxy frames from a video file.

        Returns (frames_dir_path, video_info) on success, None on failure or
        cancellation.  video_info contains: fps, width, height, frames_count,
        duration_seconds, length_bytes — collected during the extraction pass
        so the caller never needs to re-open the video file.
        """
        source = Path(video_path)
        if not self.is_video(video_path):
            return None

        frames_dir = source.parent / "frames"
        low_frames_dir = source.parent / "low_frames"

        if frames_dir.exists():
            # Frames already on disk — read metadata without re-extracting.
            return str(frames_dir), self._video_info_from_file(source)

        frames_dir.mkdir(parents=True, exist_ok=True)
        low_frames_dir.mkdir(parents=True, exist_ok=True)

        for output_dir in (frames_dir, low_frames_dir):
            for item in output_dir.iterdir():
                if item.is_file() and item.suffix.lower() in VALID_SUFFIXES:
                    item.unlink()

        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            return None

        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if on_progress is not None:
            on_progress(0)

        frame_idx = 0
        canceled = False
        while True:
            if should_cancel is not None and should_cancel():
                canceled = True
                break

            ok, frame = capture.read()
            if not ok:
                break

            out_name = f"frame_{frame_idx:06d}.jpg"
            cv2.imwrite(str(frames_dir / out_name), frame)

            h, w = frame.shape[:2]
            max_dim = max(w, h)
            scale = 1.0 if max_dim <= 320 else 320.0 / max_dim
            scaled_w = max(1, int(round(w * scale)))
            scaled_h = max(1, int(round(h * scale)))
            resized = cv2.resize(frame, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(low_frames_dir / out_name), resized)

            frame_idx += 1
            if on_progress is not None and total_frames > 0:
                on_progress(min(100, int((frame_idx * 100) / total_frames)))

        capture.release()

        if canceled:
            shutil.rmtree(frames_dir, ignore_errors=True)
            shutil.rmtree(low_frames_dir, ignore_errors=True)
            return None

        if frame_idx == 0:
            return None

        if on_progress is not None:
            on_progress(100)

        print("Finished")

        video_info = {
            "fps": fps,
            "width": width,
            "height": height,
            "frames_count": frame_idx,
            "duration_seconds": round(frame_idx / fps, 3) if fps > 0 else 0.0,
            "length_bytes": source.stat().st_size if source.is_file() else 0,
        }
        return str(frames_dir), video_info

    @staticmethod
    def _video_info_from_file(video_path: Path) -> dict:
        """Read video metadata without extracting frames (frames-already-exist path)."""
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            return {
                "fps": 0.0, "width": 0, "height": 0,
                "frames_count": 0, "duration_seconds": 0.0, "length_bytes": 0,
            }
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        capture.release()
        return {
            "fps": fps,
            "width": width,
            "height": height,
            "frames_count": frame_count,
            "duration_seconds": round(frame_count / fps, 3) if fps > 0 else 0.0,
            "length_bytes": video_path.stat().st_size if video_path.is_file() else 0,
        }
