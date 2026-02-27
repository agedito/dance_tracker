import json
from pathlib import Path

from app.interface.sequence_data import SequenceVideoData


class SequenceDataService:
    _SEQUENCE_METADATA_SUFFIX = ".dance_tracker.json"

    def read_video_data(self, frames_folder_path: str) -> SequenceVideoData | None:
        frames_folder = Path(frames_folder_path).expanduser().resolve()
        if not frames_folder.is_dir():
            return None

        metadata = self._find_matching_metadata(frames_folder)
        if not metadata:
            return None

        video_data = metadata.get("video")
        if not isinstance(video_data, dict):
            return None

        video_name = video_data.get("name")
        if not isinstance(video_name, str) or not video_name.strip():
            return None

        parent = frames_folder.parent
        video_path = parent / video_name
        data = video_data.get("data") if isinstance(video_data.get("data"), dict) else {}

        width = self._to_int(data.get("resolution", {}).get("width"))
        height = self._to_int(data.get("resolution", {}).get("height"))
        length_bytes = self._to_int(data.get("length_bytes"))
        duration_seconds = self._to_float(data.get("duration_seconds"))
        frames = self._to_int(data.get("frames_count"))
        fps = self._to_float(data.get("fps"))

        if video_path.is_file():
            if length_bytes <= 0:
                length_bytes = video_path.stat().st_size

        if frames > 0 and fps <= 0:
            fps = round(frames / duration_seconds, 3) if duration_seconds > 0 else 0.0

        return SequenceVideoData(
            resolution_width=width,
            resolution_height=height,
            length_bytes=length_bytes,
            duration_seconds=duration_seconds,
            frames=frames,
            fps=fps,
        )

    def read_bookmarks(self, frames_folder_path: str) -> list[int]:
        frames_folder = Path(frames_folder_path).expanduser().resolve()
        if not frames_folder.is_dir():
            return []

        metadata_path = self._find_matching_metadata_path(frames_folder)
        if metadata_path is None:
            return []

        payload = self._read_json(metadata_path)
        if payload is None:
            return []

        return self._extract_bookmarks(payload)

    def add_bookmark(self, frames_folder_path: str, frame: int) -> list[int]:
        return self._update_bookmarks(
            frames_folder_path,
            updater=lambda bookmarks: self._insert_bookmark(bookmarks, frame),
        )

    def move_bookmark(self, frames_folder_path: str, source_frame: int, target_frame: int) -> list[int]:
        def _move(bookmarks: list[int]) -> list[int]:
            if source_frame not in bookmarks:
                return bookmarks
            updated = [value for value in bookmarks if value != source_frame]
            return self._insert_bookmark(updated, target_frame)

        return self._update_bookmarks(frames_folder_path, updater=_move)

    def remove_bookmark(self, frames_folder_path: str, frame: int) -> list[int]:
        return self._update_bookmarks(
            frames_folder_path,
            updater=lambda bookmarks: [value for value in bookmarks if value != frame],
        )

    def _find_matching_metadata(self, frames_folder: Path) -> dict | None:
        metadata_path = self._find_matching_metadata_path(frames_folder)
        if metadata_path is None:
            return None
        return self._read_json(metadata_path)

    def _find_matching_metadata_path(self, frames_folder: Path) -> Path | None:
        metadata_files = sorted(frames_folder.parent.glob(f"*{self._SEQUENCE_METADATA_SUFFIX}"))
        target = frames_folder.resolve()

        for metadata_path in metadata_files:
            payload = self._read_json(metadata_path)
            if not payload:
                continue

            frames_value = payload.get("frames") or payload.get("frames_path")
            resolved_frames = self._resolve_metadata_path(frames_value, metadata_path.parent)
            if resolved_frames and resolved_frames == target:
                return metadata_path

        return None

    def _update_bookmarks(self, frames_folder_path: str, updater) -> list[int]:
        frames_folder = Path(frames_folder_path).expanduser().resolve()
        if not frames_folder.is_dir():
            return []

        metadata_path = self._find_matching_metadata_path(frames_folder)
        if metadata_path is None:
            return []

        payload = self._read_json(metadata_path)
        if payload is None:
            return []

        bookmarks = self._extract_bookmarks(payload)
        updated = updater(bookmarks)
        sequence = payload.get("sequence")
        if not isinstance(sequence, dict):
            sequence = {}
            payload["sequence"] = sequence
        sequence["bookmarks"] = updated

        metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return updated

    @staticmethod
    def _extract_bookmarks(payload: dict) -> list[int]:
        sequence = payload.get("sequence")
        if not isinstance(sequence, dict):
            return []

        raw_bookmarks = sequence.get("bookmarks")
        if not isinstance(raw_bookmarks, list):
            return []

        values = {item for item in (SequenceDataService._to_int(value) for value in raw_bookmarks) if item >= 0}
        return sorted(values)

    @staticmethod
    def _insert_bookmark(bookmarks: list[int], frame: int) -> list[int]:
        normalized = max(0, int(frame))
        updated = set(bookmarks)
        updated.add(normalized)
        return sorted(updated)

    @staticmethod
    def _resolve_metadata_path(value: object, root: Path) -> Path | None:
        if not isinstance(value, str) or not value.strip():
            return None

        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        return candidate

    @staticmethod
    def _read_json(path: Path) -> dict | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _to_int(value: object) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _to_float(value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
