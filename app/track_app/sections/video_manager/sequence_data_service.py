import json
from pathlib import Path

from app.interface.sequence_data import Bookmark, SequenceVideoData


class SequenceDataService:
    _SEQUENCE_METADATA_SUFFIX = ".dance_tracker.json"
    _MIN_BOOKMARK_DISTANCE_FRAMES = 25
    _DEFAULT_DANCE_INFO = {
        "dance_style": "Argentine Tango",
        "song": "Golden Night",
        "follower": "Alex Morgan",
        "leader": "Jamie Rivera",
        "event": "Milonga Sunset",
        "year": "2024",
    }

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
        sequence_data = metadata.get("sequence") if isinstance(metadata.get("sequence"), dict) else {}

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

        dance_style = self._string_or_default(
            sequence_data.get("dance_style"),
            self._DEFAULT_DANCE_INFO["dance_style"],
        )
        song = self._string_or_default(sequence_data.get("song"), self._DEFAULT_DANCE_INFO["song"])
        follower = self._string_or_default(sequence_data.get("follower"), self._DEFAULT_DANCE_INFO["follower"])
        leader = self._string_or_default(sequence_data.get("leader"), self._DEFAULT_DANCE_INFO["leader"])
        event = self._string_or_default(sequence_data.get("event"), self._DEFAULT_DANCE_INFO["event"])
        year = self._string_or_default(sequence_data.get("year"), self._DEFAULT_DANCE_INFO["year"])

        return SequenceVideoData(
            resolution_width=width,
            resolution_height=height,
            length_bytes=length_bytes,
            duration_seconds=duration_seconds,
            frames=frames,
            fps=fps,
            dance_style=dance_style,
            song=song,
            follower=follower,
            leader=leader,
            event=event,
            year=year,
        )

    def read_bookmarks(self, frames_folder_path: str) -> list[Bookmark]:
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

    def add_bookmark(self, frames_folder_path: str, frame: int) -> list[Bookmark]:
        return self._update_bookmarks(
            frames_folder_path,
            updater=lambda bookmarks: self._insert_bookmark(bookmarks, frame),
        )

    def move_bookmark(self, frames_folder_path: str, source_frame: int, target_frame: int) -> list[Bookmark]:
        def _move(bookmarks: list[Bookmark]) -> list[Bookmark]:
            if source_frame not in {bookmark.frame for bookmark in bookmarks}:
                return bookmarks

            source_name = ""
            source_locked = False
            for bookmark in bookmarks:
                if bookmark.frame == source_frame:
                    source_name = bookmark.name
                    source_locked = bookmark.locked
                    break

            if source_locked:
                return bookmarks

            updated = [bookmark for bookmark in bookmarks if bookmark.frame != source_frame]
            preferred_direction = 1 if source_frame > target_frame else -1
            adjusted_target = self._resolve_move_target_frame(
                bookmarks=updated,
                target_frame=target_frame,
                preferred_direction=preferred_direction,
            )
            return self._insert_bookmark(
                updated,
                adjusted_target,
                source_name,
                locked=source_locked,
                allow_nearby=False,
            )

        return self._update_bookmarks(frames_folder_path, updater=_move)

    def remove_bookmark(self, frames_folder_path: str, frame: int) -> list[Bookmark]:
        return self._update_bookmarks(
            frames_folder_path,
            updater=lambda bookmarks: [
                bookmark
                for bookmark in bookmarks
                if bookmark.frame != frame or bookmark.locked
            ],
        )

    def set_bookmark_name(self, frames_folder_path: str, frame: int, name: str) -> list[Bookmark]:
        normalized_name = self._normalize_name(name)

        def _set_name(bookmarks: list[Bookmark]) -> list[Bookmark]:
            updated: list[Bookmark] = []
            for bookmark in bookmarks:
                if bookmark.frame == frame:
                    if bookmark.locked:
                        updated.append(bookmark)
                    else:
                        updated.append(
                            Bookmark(frame=bookmark.frame, name=normalized_name, locked=bookmark.locked)
                        )
                else:
                    updated.append(bookmark)
            return updated

        return self._update_bookmarks(frames_folder_path, updater=_set_name)

    def set_bookmark_locked(self, frames_folder_path: str, frame: int, locked: bool) -> list[Bookmark]:
        def _set_locked(bookmarks: list[Bookmark]) -> list[Bookmark]:
            updated: list[Bookmark] = []
            for bookmark in bookmarks:
                if bookmark.frame == frame:
                    updated.append(Bookmark(frame=bookmark.frame, name=bookmark.name, locked=locked))
                else:
                    updated.append(bookmark)
            return updated

        return self._update_bookmarks(frames_folder_path, updater=_set_locked)

    def get_sequence_name(self, frames_folder_path: str) -> str | None:
        frames_folder = Path(frames_folder_path).expanduser().resolve()
        metadata_path = self._find_matching_metadata_path(frames_folder)
        if metadata_path is None:
            return None
        payload = self._read_json(metadata_path)
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
        metadata_path = self._find_matching_metadata_path(frames_folder)
        if metadata_path is None:
            return
        payload = self._read_json(metadata_path)
        if payload is None:
            return
        sequence = payload.get("sequence")
        if not isinstance(sequence, dict):
            sequence = {}
            payload["sequence"] = sequence
        sequence["name"] = name.strip()
        metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

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

    def _update_bookmarks(self, frames_folder_path: str, updater) -> list[Bookmark]:
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
        sequence["bookmarks"] = [
            {
                "frame": bookmark.frame,
                "name": bookmark.name,
                "locked": bookmark.locked,
            }
            for bookmark in updated
        ]

        metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return updated

    @staticmethod
    def _extract_bookmarks(payload: dict) -> list[Bookmark]:
        sequence = payload.get("sequence")
        if not isinstance(sequence, dict):
            return []

        raw_bookmarks = sequence.get("bookmarks")
        if not isinstance(raw_bookmarks, list):
            return []

        values: dict[int, Bookmark] = {}
        for raw_bookmark in raw_bookmarks:
            if isinstance(raw_bookmark, dict):
                frame = SequenceDataService._to_int(raw_bookmark.get("frame"))
                name = SequenceDataService._normalize_name(raw_bookmark.get("name"))
                locked = bool(raw_bookmark.get("locked", False))
            else:
                frame = SequenceDataService._to_int(raw_bookmark)
                name = ""
                locked = False

            if frame < 0:
                continue
            values[frame] = Bookmark(frame=frame, name=name, locked=locked)

        return [
            values[frame]
            for frame in sorted(values)
        ]

    @staticmethod
    def _insert_bookmark(
        bookmarks: list[Bookmark],
        frame: int,
        name: str = "",
        locked: bool = False,
        allow_nearby: bool = False,
    ) -> list[Bookmark]:
        normalized = max(0, int(frame))
        normalized_name = SequenceDataService._normalize_name(name)
        by_frame = {
            bookmark.frame: Bookmark(frame=bookmark.frame, name=bookmark.name, locked=bookmark.locked)
            for bookmark in bookmarks
        }

        if not allow_nearby and SequenceDataService._is_too_close_to_existing_bookmark(bookmarks, normalized):
            return [by_frame[item] for item in sorted(by_frame)]

        by_frame[normalized] = Bookmark(frame=normalized, name=normalized_name, locked=locked)
        return [by_frame[item] for item in sorted(by_frame)]

    @staticmethod
    def _resolve_move_target_frame(bookmarks: list[Bookmark], target_frame: int, preferred_direction: int) -> int:
        candidate = max(0, int(target_frame))
        if not SequenceDataService._is_too_close_to_existing_bookmark(bookmarks, candidate):
            return candidate

        direction = 1 if preferred_direction >= 0 else -1
        while True:
            conflict = SequenceDataService._find_conflict(bookmarks, candidate)
            if conflict is None:
                return candidate

            if direction > 0:
                candidate = conflict + SequenceDataService._MIN_BOOKMARK_DISTANCE_FRAMES
                continue

            next_candidate = conflict - SequenceDataService._MIN_BOOKMARK_DISTANCE_FRAMES
            if next_candidate < 0:
                direction = 1
                continue
            candidate = next_candidate

    @staticmethod
    def _find_conflict(bookmarks: list[Bookmark], frame: int) -> int | None:
        minimum_gap = SequenceDataService._MIN_BOOKMARK_DISTANCE_FRAMES
        for bookmark in sorted(bookmarks, key=lambda item: abs(item.frame - frame)):
            if abs(bookmark.frame - frame) < minimum_gap:
                return bookmark.frame
        return None

    @staticmethod
    def _is_too_close_to_existing_bookmark(bookmarks: list[Bookmark], frame: int) -> bool:
        return SequenceDataService._find_conflict(bookmarks, frame) is not None

    @staticmethod
    def _normalize_name(value: object) -> str:
        if not isinstance(value, str):
            return ""
        return value.strip()

    @staticmethod
    def _string_or_default(value: object, default: str) -> str:
        if not isinstance(value, str):
            return default
        normalized = value.strip()
        return normalized or default

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
