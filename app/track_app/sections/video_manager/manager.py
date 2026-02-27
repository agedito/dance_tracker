from collections.abc import Callable
from pathlib import Path
import shutil
import json

import cv2

VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}
VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


class VideoManager:
    _SEQUENCE_METADATA_SUFFIX = ".dance_tracker.json"

    @staticmethod
    def is_video(video_path: str) -> bool:
        source = Path(video_path)
        if not source.exists() or not source.is_file():
            return False

        if source.suffix.lower() not in VIDEO_SUFFIXES:
            return False

        return True

    def extract_frames(
        self,
        video_path: str,
        on_progress: Callable[[int], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> str | None:
        source = Path(video_path)
        if not self.is_video(video_path):
            return None

        frames_dir = source.parent / "frames"
        low_frames_dir = source.parent / "low_frames"
        if frames_dir.exists():
            return str(frames_dir)

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
        return str(frames_dir)

    @classmethod
    def is_sequence_metadata(cls, file_path: str) -> bool:
        source = Path(file_path)
        return source.is_file() and source.suffix.lower() == ".json"

    @classmethod
    def metadata_path_for_video(cls, video_path: str) -> Path:
        source = Path(video_path)
        return source.with_name(f"{source.stem}{cls._SEQUENCE_METADATA_SUFFIX}")

    @classmethod
    def write_sequence_metadata(cls, video_path: str, frames_path: str) -> str | None:
        source = Path(video_path)
        if not source.is_file():
            return None

        metadata_path = cls.metadata_path_for_video(video_path)
        frames_dir = Path(frames_path).resolve()
        low_frames_dir = frames_dir.with_name("low_frames")
        if not low_frames_dir.is_dir():
            legacy_low_frames_dir = frames_dir.with_name("frames_mino")
            if legacy_low_frames_dir.is_dir():
                low_frames_dir = legacy_low_frames_dir
        video_info = cls._read_video_info(source)

        payload = {
            "sequence": {
                "name": source.stem,
            },
            "video": {
                "name": source.name,
                "data": {
                    "duration_seconds": video_info["duration_seconds"],
                    "resolution": {
                        "width": video_info["width"],
                        "height": video_info["height"],
                    },
                    "frames_count": video_info["frames_count"],
                },
            },
            "frames": cls._relative_to_parent_or_absolute(frames_dir, source.parent),
            "low_frames": cls._relative_to_parent_or_absolute(low_frames_dir, source.parent),
        }
        metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(metadata_path)

    @staticmethod
    def _relative_to_parent_or_absolute(path: Path, parent: Path) -> str:
        try:
            return str(path.relative_to(parent.resolve()))
        except ValueError:
            return str(path)

    @staticmethod
    def _read_video_info(video_path: Path) -> dict[str, float | int]:
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            return {
                "duration_seconds": 0.0,
                "width": 0,
                "height": 0,
                "frames_count": 0,
            }

        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        capture.release()

        duration_seconds = round(frame_count / fps, 3) if fps > 0 else 0.0
        return {
            "duration_seconds": duration_seconds,
            "width": width,
            "height": height,
            "frames_count": frame_count,
        }

    @classmethod
    def read_sequence_metadata(cls, metadata_path: str) -> dict | None:
        source = Path(metadata_path)
        if not source.is_file() or source.suffix.lower() != ".json":
            return None

        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(data, dict):
            return None

        return data
