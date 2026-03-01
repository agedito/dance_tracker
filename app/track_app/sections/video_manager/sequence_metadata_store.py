import json
from pathlib import Path

_SUFFIX = ".dance_tracker.json"


class SequenceMetadataStore:
    """Reads and writes .dance_tracker.json sequence metadata files.

    Single responsibility: all I/O for the sidecar metadata that links a video
    file to its extracted frames directory.
    """

    @staticmethod
    def is_sequence_metadata(file_path: str) -> bool:
        source = Path(file_path)
        return source.is_file() and source.suffix.lower() == ".json"

    @staticmethod
    def path_for_video(video_path: str) -> Path:
        source = Path(video_path)
        return source.with_name(f"{source.stem}{_SUFFIX}")

    @classmethod
    def write(cls, video_path: str, frames_path: str, video_info: dict) -> str | None:
        """Write (or overwrite) the sidecar JSON for a video/frames pair.

        video_info must contain: fps, width, height, frames_count,
        duration_seconds, length_bytes.
        """
        source = Path(video_path)
        if not source.is_file():
            return None

        metadata_path = cls.path_for_video(video_path)
        frames_dir = Path(frames_path).resolve()

        low_frames_dir = frames_dir.with_name("low_frames")
        if not low_frames_dir.is_dir():
            legacy = frames_dir.with_name("frames_mino")
            if legacy.is_dir():
                low_frames_dir = legacy

        payload = {
            "sequence": {"name": source.stem},
            "video": {
                "name": source.name,
                "data": {
                    "duration_seconds": video_info.get("duration_seconds", 0.0),
                    "resolution": {
                        "width": video_info.get("width", 0),
                        "height": video_info.get("height", 0),
                    },
                    "frames_count": video_info.get("frames_count", 0),
                    "fps": video_info.get("fps", 0.0),
                    "length_bytes": video_info.get("length_bytes", 0),
                },
            },
            "frames": cls._relative_or_absolute(frames_dir, source.parent),
            "low_frames": cls._relative_or_absolute(low_frames_dir, source.parent),
        }
        metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(metadata_path)

    @staticmethod
    def read(metadata_path: str) -> dict | None:
        source = Path(metadata_path)
        if not source.is_file() or source.suffix.lower() != ".json":
            return None
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _relative_or_absolute(path: Path, parent: Path) -> str:
        try:
            return str(path.relative_to(parent.resolve()))
        except ValueError:
            return str(path)
