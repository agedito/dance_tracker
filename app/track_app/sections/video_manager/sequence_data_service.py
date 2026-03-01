from pathlib import Path

from app.interface.sequence_data import Bookmark, SequenceVideoData
from app.track_app.sections.video_manager import bookmark_domain, sequence_file_store


class SequenceDataService:
    def read_video_data(self, frames_folder_path: str) -> SequenceVideoData | None:
        frames_folder = Path(frames_folder_path).expanduser().resolve()
        if not frames_folder.is_dir():
            return None

        metadata_path = sequence_file_store.find_metadata_for_frames(frames_folder)
        if metadata_path is None:
            return None

        metadata = sequence_file_store.read(metadata_path)
        if not metadata:
            return None

        video_data = metadata.get("video")
        if not isinstance(video_data, dict):
            return None

        video_name = video_data.get("name")
        if not isinstance(video_name, str) or not video_name.strip():
            return None

        data = video_data.get("data") if isinstance(video_data.get("data"), dict) else {}
        sequence_data = metadata.get("sequence") if isinstance(metadata.get("sequence"), dict) else {}

        width = _to_int(data.get("resolution", {}).get("width"))
        height = _to_int(data.get("resolution", {}).get("height"))
        length_bytes = _to_int(data.get("length_bytes"))
        duration_seconds = _to_float(data.get("duration_seconds"))
        frames = _to_int(data.get("frames_count"))
        fps = _to_float(data.get("fps"))

        video_path = frames_folder.parent / video_name
        if video_path.is_file() and length_bytes <= 0:
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
            dance_style=_to_str(sequence_data.get("dance_style")),
            song=_to_str(sequence_data.get("song")),
            follower=_to_str(sequence_data.get("follower")),
            leader=_to_str(sequence_data.get("leader")),
            event=_to_str(sequence_data.get("event")),
            year=_to_str(sequence_data.get("year")),
        )

    def read_bookmarks(self, frames_folder_path: str) -> list[Bookmark]:
        frames_folder = Path(frames_folder_path).expanduser().resolve()
        if not frames_folder.is_dir():
            return []

        metadata_path = sequence_file_store.find_metadata_for_frames(frames_folder)
        if metadata_path is None:
            return []

        payload = sequence_file_store.read(metadata_path)
        if payload is None:
            return []

        return bookmark_domain.extract_bookmarks(payload)

    def add_bookmark(self, frames_folder_path: str, frame: int) -> list[Bookmark]:
        return self._update_bookmarks(
            frames_folder_path,
            updater=lambda bookmarks: bookmark_domain.insert_bookmark(bookmarks, frame),
        )

    def move_bookmark(self, frames_folder_path: str, source_frame: int, target_frame: int) -> list[Bookmark]:
        return self._update_bookmarks(
            frames_folder_path,
            updater=lambda bookmarks: bookmark_domain.apply_move(bookmarks, source_frame, target_frame),
        )

    def remove_bookmark(self, frames_folder_path: str, frame: int) -> list[Bookmark]:
        return self._update_bookmarks(
            frames_folder_path,
            updater=lambda bookmarks: [b for b in bookmarks if b.frame != frame or b.locked],
        )

    def set_bookmark_name(self, frames_folder_path: str, frame: int, name: str) -> list[Bookmark]:
        normalized = bookmark_domain.normalize_name(name)

        def _apply(bookmarks: list[Bookmark]) -> list[Bookmark]:
            return [
                Bookmark(frame=b.frame, name=normalized, locked=b.locked)
                if b.frame == frame and not b.locked
                else b
                for b in bookmarks
            ]

        return self._update_bookmarks(frames_folder_path, updater=_apply)

    def set_bookmark_locked(self, frames_folder_path: str, frame: int, locked: bool) -> list[Bookmark]:
        def _apply(bookmarks: list[Bookmark]) -> list[Bookmark]:
            return [
                Bookmark(frame=b.frame, name=b.name, locked=locked) if b.frame == frame else b
                for b in bookmarks
            ]

        return self._update_bookmarks(frames_folder_path, updater=_apply)

    def get_sequence_name(self, frames_folder_path: str) -> str | None:
        frames_folder = Path(frames_folder_path).expanduser().resolve()
        metadata_path = sequence_file_store.find_metadata_for_frames(frames_folder)
        if metadata_path is None:
            return None

        payload = sequence_file_store.read(metadata_path)
        if payload is None:
            return None

        sequence = payload.get("sequence")
        if not isinstance(sequence, dict):
            return None

        value = sequence.get("name")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def set_sequence_name(self, frames_folder_path: str, name: str) -> None:
        frames_folder = Path(frames_folder_path).expanduser().resolve()
        metadata_path = sequence_file_store.find_metadata_for_frames(frames_folder)
        if metadata_path is None:
            return

        payload = sequence_file_store.read(metadata_path)
        if payload is None:
            return

        payload.setdefault("sequence", {})["name"] = name.strip()
        sequence_file_store.write_payload(metadata_path, payload)

    def previous_bookmark_frame(self, frames_folder_path: str, current_frame: int) -> int | None:
        bookmarks = self.read_bookmarks(frames_folder_path)
        candidates = sorted(b.frame for b in bookmarks if b.frame < current_frame)
        return candidates[-1] if candidates else None

    def next_bookmark_frame(self, frames_folder_path: str, current_frame: int) -> int | None:
        bookmarks = self.read_bookmarks(frames_folder_path)
        candidates = sorted(b.frame for b in bookmarks if b.frame > current_frame)
        return candidates[0] if candidates else None

    def _update_bookmarks(self, frames_folder_path: str, updater) -> list[Bookmark]:
        frames_folder = Path(frames_folder_path).expanduser().resolve()
        if not frames_folder.is_dir():
            return []

        metadata_path = sequence_file_store.find_metadata_for_frames(frames_folder)
        if metadata_path is None:
            return []

        payload = sequence_file_store.read(metadata_path)
        if payload is None:
            return []

        current = bookmark_domain.extract_bookmarks(payload)
        updated = updater(current)
        payload.setdefault("sequence", {})["bookmarks"] = [
            {"frame": b.frame, "name": b.name, "locked": b.locked}
            for b in updated
        ]
        sequence_file_store.write_payload(metadata_path, payload)
        return updated


def _to_int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _to_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_str(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()
