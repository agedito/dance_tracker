import json
import re
import shutil
from collections.abc import Callable
from pathlib import Path

from app.interface.event_bus import EventBus, Event
from app.interface.music import SongMetadata, SongStatus
from app.interface.sequence_data import SequenceDataPort
from app.interface.track_detector import PersonDetection
from app.interface.sequences import SequenceItem, SequenceState
from app.track_app.main_app import DanceTrackerApp
from app.track_app.sections.video_manager.manager import VIDEO_SUFFIXES
from app.track_app.sections.video_manager.sequence_data_service import SequenceDataService

_PREFS_PATH = Path.home() / ".dance_tracker_prefs.json"


class MediaAdapter:
    def __init__(self, app: DanceTrackerApp, events: EventBus):
        self._app = app
        self._events = events

    def load(
        self,
        path: str,
        on_progress: Callable[[int], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> None:
        print("Loading", path)

        path = self._resolve_input_path(
            path,
            on_progress=on_progress,
            should_cancel=should_cancel,
        )

        if not path:
            return

        if self._app.video_manager.is_video(path):
            path = self._load_video(path, on_progress=on_progress, should_cancel=should_cancel)

        if not path:
            return

        if not Path(path).is_dir():
            print("It's not a folder")
            return

        self._events.emit(Event.FramesLoaded, path)

    def _resolve_input_path(
        self,
        path: str,
        on_progress: Callable[[int], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> str | None:
        if not self._app.video_manager.is_sequence_metadata(path):
            return path

        metadata = self._app.video_manager.read_sequence_metadata(path)
        if not metadata:
            return None

        metadata_root = Path(path).expanduser().parent

        frames_path = metadata.get("frames") or metadata.get("frames_path")
        resolved_frames = self._resolve_metadata_path(frames_path, metadata_root)
        if resolved_frames and resolved_frames.is_dir():
            return str(resolved_frames)

        video_path = self._video_path_from_metadata(metadata)
        resolved_video = self._resolve_metadata_path(video_path, metadata_root)
        if resolved_video and self._app.video_manager.is_video(str(resolved_video)):
            return self._load_video(str(resolved_video), on_progress=on_progress, should_cancel=should_cancel)

        return None

    @staticmethod
    def _resolve_metadata_path(value: object, root: Path) -> Path | None:
        if not isinstance(value, str) or not value.strip():
            return None

        candidate = Path(value).expanduser()
        if candidate.is_absolute():
            return candidate
        return (root / candidate).resolve()

    @staticmethod
    def _video_path_from_metadata(metadata: dict) -> str | None:
        legacy_video_path = metadata.get("video_path")
        if isinstance(legacy_video_path, str) and legacy_video_path.strip():
            return legacy_video_path

        video_data = metadata.get("video")
        if not isinstance(video_data, dict):
            return None

        video_name = video_data.get("name") or video_data.get("nombre")
        if not isinstance(video_name, str) or not video_name.strip():
            return None

        return video_name

    def _load_video(
        self,
        path: str,
        on_progress: Callable[[int], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> str | None:
        if not self._app.video_manager.is_video(path):
            return path

        song = SongMetadata(status=SongStatus.NOT_RUN)
        try:
            song = self._app.music_identifier.identify_from_video(path)
        except Exception as err:
            song = SongMetadata(
                status=SongStatus.ERROR,
                provider="music_identifier",
                message=f"Error identifying song: {err}",
            )

        self._events.emit(Event.SongIdentified, song)

        frames_path = self._app.video_manager.extract_frames(
            path,
            on_progress=on_progress,
            should_cancel=should_cancel,
        )
        print("Video extracted at", frames_path)

        if not frames_path:
            return None

        self._app.video_manager.write_sequence_metadata(path, frames_path)
        return frames_path


class SequencesAdapter:
    def __init__(self, media: MediaAdapter, events: EventBus, max_recent_folders: int):
        self._media = media
        self._events = events
        self._max_recent_folders = max_recent_folders
        self._active_folder: str | None = None
        self._events.on(Event.FramesLoaded, self._on_frames_loaded)

    def refresh(self) -> None:
        self._emit_state()

    def load(self, folder_path: str) -> None:
        self._active_folder = self._normalize(folder_path)
        self._emit_state()
        self._media.load(folder_path)

    def move(self, dragged_folder: str, target_folder: str, drop_after: bool) -> None:
        dragged = self._normalize(dragged_folder)
        target = self._normalize(target_folder)

        folders = self._recent_folders()
        if dragged not in folders or target not in folders or dragged == target:
            return

        updated = [folder for folder in folders if folder != dragged]
        target_idx = updated.index(target)
        if drop_after:
            target_idx += 1
        updated.insert(target_idx, dragged)

        prefs = self._load_preferences()
        prefs["recent_folders"] = updated[: self._max_recent_folders]
        self._save_preferences(prefs)
        self._emit_state()

    def remove(self, folder_path: str) -> None:
        normalized = self._normalize(folder_path)
        prefs = self._load_preferences()

        folders = [folder for folder in self._recent_folders(prefs) if folder != normalized]
        prefs["recent_folders"] = folders[: self._max_recent_folders]

        if prefs.get("last_opened_folder") == normalized:
            prefs["last_opened_folder"] = folders[0] if folders else None

        frames = prefs.get("last_frame_by_folder")
        if isinstance(frames, dict):
            frames.pop(normalized, None)
            prefs["last_frame_by_folder"] = frames

        thumbnails = prefs.get("recent_folder_thumbnails")
        if isinstance(thumbnails, dict):
            thumbnails.pop(normalized, None)
            prefs["recent_folder_thumbnails"] = thumbnails

        if self._active_folder == normalized:
            self._active_folder = None

        self._save_preferences(prefs)
        self._emit_state()

    def delete_video_and_frames(self, folder_path: str) -> None:
        folder = Path(folder_path).expanduser()
        video_file = self._find_video_for_frames(folder)

        if folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)

        if folder.name == "frames":
            low_frames = folder.parent / "low_frames"
            if low_frames.is_dir():
                shutil.rmtree(low_frames, ignore_errors=True)

            legacy_low_frames = folder.parent / "frames_mino"
            if legacy_low_frames.is_dir():
                shutil.rmtree(legacy_low_frames, ignore_errors=True)

        if video_file and video_file.exists():
            video_file.unlink(missing_ok=True)

        self.remove(folder_path)

    def last_opened_folder(self) -> str | None:
        value = self._load_preferences().get("last_opened_folder")
        return value if isinstance(value, str) and value else None

    def _on_frames_loaded(self, path: str) -> None:
        normalized = self._normalize(path)
        prefs = self._load_preferences()
        folders = self._recent_folders(prefs)

        if normalized not in folders:
            folders.append(normalized)

        prefs["recent_folders"] = folders[: self._max_recent_folders]
        prefs["last_opened_folder"] = normalized

        thumbnails = prefs.get("recent_folder_thumbnails")
        if not isinstance(thumbnails, dict):
            thumbnails = {}

        thumbnail = self._thumbnail_from_frame(normalized)
        if thumbnail is None:
            thumbnails.pop(normalized, None)
        else:
            thumbnails[normalized] = thumbnail
        prefs["recent_folder_thumbnails"] = thumbnails

        self._active_folder = normalized
        self._save_preferences(prefs)
        self._emit_state()

    def _emit_state(self) -> None:
        prefs = self._load_preferences()
        thumbnails = prefs.get("recent_folder_thumbnails", {})
        if not isinstance(thumbnails, dict):
            thumbnails = {}

        items = [
            SequenceItem(folder_path=folder, thumbnail_path=thumbnails.get(folder))
            for folder in self._recent_folders(prefs)
        ]
        self._events.emit(Event.SequencesChanged, SequenceState(items=items, active_folder=self._active_folder))

    def _recent_folders(self, prefs: dict | None = None) -> list[str]:
        payload = prefs or self._load_preferences()
        folders = payload.get("recent_folders", [])
        if not isinstance(folders, list):
            return []
        return [self._normalize(folder) for folder in folders if isinstance(folder, str) and folder][: self._max_recent_folders]

    @staticmethod
    def _find_video_for_frames(folder: Path) -> Path | None:
        parent = folder.parent
        if not parent.is_dir():
            return None

        videos = [
            file
            for file in sorted(parent.iterdir())
            if file.is_file() and file.suffix.lower() in VIDEO_SUFFIXES
        ]
        return videos[0] if videos else None

    @staticmethod
    def _thumbnail_from_frame(folder_path: str) -> str | None:
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return None

        valid_suffixes = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
        frame_files = [
            file
            for file in sorted(folder.iterdir(), key=SequencesAdapter._natural_sort_key)
            if file.is_file() and file.suffix.lower() in valid_suffixes
        ]
        if not frame_files:
            return None

        target_idx = 300 if len(frame_files) > 300 else len(frame_files) // 2
        return str(frame_files[target_idx])

    @staticmethod
    def _natural_sort_key(path: Path):
        chunks = re.split(r"(\d+)", path.name.lower())
        return [int(chunk) if chunk.isdigit() else chunk for chunk in chunks]

    @staticmethod
    def _normalize(path: str) -> str:
        return str(Path(path).expanduser())

    @staticmethod
    def _load_preferences() -> dict:
        if not _PREFS_PATH.exists():
            return {}
        try:
            payload = json.loads(_PREFS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _save_preferences(payload: dict) -> None:
        _PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _PREFS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class FramesAdapter:
    def __init__(self, app: DanceTrackerApp):
        self._state = app.states_manager

    @property
    def fps(self) -> int:
        return self._state.fps

    @property
    def total_frames(self) -> int:
        return self._state.total_frames

    @property
    def layers(self) -> list:
        return self._state.layers

    @property
    def error_frames(self) -> list[int]:
        return self._state.error_frames

    @property
    def cur_frame(self) -> int:
        return self._state.cur_frame

    @property
    def playing(self) -> bool:
        return self._state.playing

    @property
    def frame_cache_radius(self) -> int:
        return self._state.config.frame_cache_radius

    def set_frame(self, frame: int) -> int:
        return self._state.set_frame(frame)

    def set_total_frames(self, total_frames: int) -> None:
        self._state.set_total_frames(total_frames)

    def play(self) -> None:
        self._state.play()

    def pause(self) -> None:
        self._state.pause()

    def step(self, delta: int) -> int:
        return self._state.step(delta)

    def go_to_start(self) -> int:
        return self._state.go_to_start()

    def go_to_end(self) -> int:
        return self._state.go_to_end()

    def next_error_frame(self) -> int | None:
        return self._state.next_error_frame()

    def prev_error_frame(self) -> int | None:
        return self._state.prev_error_frame()

    def advance_if_playing(self) -> bool:
        return self._state.advance_if_playing()


class SequenceDataAdapter:
    def __init__(self):
        self._service: SequenceDataPort = SequenceDataService()

    def read_video_data(self, frames_folder_path: str):
        return self._service.read_video_data(frames_folder_path)


class TrackDetectorAdapter:
    def __init__(self, app: DanceTrackerApp, events: EventBus):
        self._service = app.track_detector
        self._events = events

    def detect_people_for_sequence(self, frames_folder_path: str) -> int:
        detected_frames = self._service.detect_people_for_sequence(frames_folder_path)
        self._events.emit(Event.DetectionsUpdated, frames_folder_path)
        return detected_frames

    def load_detections(self, frames_folder_path: str) -> None:
        self._service.load_detections(frames_folder_path)
        self._events.emit(Event.DetectionsUpdated, frames_folder_path)

    def detections_for_frame(self, frame_index: int) -> list[PersonDetection]:
        return self._service.detections_for_frame(frame_index)


class AppAdapter:
    def __init__(self, app: DanceTrackerApp, events: EventBus):
        self.media = MediaAdapter(app, events)
        self.sequences = SequencesAdapter(self.media, events, max_recent_folders=app.cfg.max_recent_folders)
        self.frames = FramesAdapter(app)
        self.sequence_data = SequenceDataAdapter()
        self.track_detector = TrackDetectorAdapter(app, events)
