import shutil
from collections.abc import Callable
from pathlib import Path

from app.interface.event_bus import EventBus, Event
from app.interface.music import MusicPort, SongMetadata, SongStatus
from app.interface.sequence_data import Bookmark, SequenceDataPort
from app.interface.sequence_prefs import SequencePreferencesPort
from app.interface.sequences import SequenceItem, SequenceState
from app.interface.track_detector import PersonDetection
from app.track_app.main_app import DanceTrackerApp
from app.track_app.sections.video_manager.manager import VIDEO_SUFFIXES
from app.track_app.sections.video_manager.sequence_data_service import SequenceDataService
from app.track_app.sections.video_manager.sequence_metadata_store import SequenceMetadataStore
from app.track_app.sections.video_manager import sequence_file_store


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

        path = self._resolve_input_path(path)
        if not path:
            return

        if self._app.video_manager.is_video(path):
            self._identify_song(path)
            path = self._extract_video(path, on_progress=on_progress, should_cancel=should_cancel)

        if not path:
            return

        if not Path(path).is_dir():
            print("It's not a folder")
            return

        self._events.emit(Event.FramesLoaded, path)

    def _resolve_input_path(self, path: str) -> str | None:
        """Pure path resolution: returns the frames dir or video path to load, no side effects."""
        if not SequenceMetadataStore.is_sequence_metadata(path):
            return path

        metadata = SequenceMetadataStore.read(path)
        if not metadata:
            return None

        metadata_root = Path(path).expanduser().parent

        frames_value = metadata.get("frames") or metadata.get("frames_path")
        resolved_frames = sequence_file_store.resolve_path(frames_value, metadata_root)
        if resolved_frames and resolved_frames.is_dir():
            return str(resolved_frames)

        video_value = sequence_file_store.video_path_from_metadata(metadata)
        resolved_video = sequence_file_store.resolve_path(video_value, metadata_root)
        if resolved_video and self._app.video_manager.is_video(str(resolved_video)):
            return str(resolved_video)

        return None

    def _identify_song(self, video_path: str) -> None:
        try:
            song = self._app.music_identifier.identify_from_video(video_path)
        except Exception as err:
            song = SongMetadata(
                status=SongStatus.ERROR,
                provider="music_identifier",
                message=f"Error identifying song: {err}",
            )
        self._events.emit(Event.SongIdentified, song)

    def _extract_video(
        self,
        path: str,
        on_progress: Callable[[int], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> str | None:
        result = self._app.video_manager.extract_frames(
            path,
            on_progress=on_progress,
            should_cancel=should_cancel,
        )
        if not result:
            return None

        frames_path, video_info = result
        print("Video extracted at", frames_path)
        self._app.sequence_metadata.write(path, frames_path, video_info)
        return frames_path


class MusicAdapter:
    def __init__(self, app: DanceTrackerApp, events: EventBus):
        self._app = app
        self._events = events

    def analyze_for_sequence(self, frames_folder_path: str) -> SongMetadata:
        video_path = self._resolve_video_path(frames_folder_path)
        if not video_path:
            song = SongMetadata(
                status=SongStatus.UNAVAILABLE,
                provider="music_identifier",
                message="Could not resolve the source video for this sequence.",
            )
            self._events.emit(Event.SongIdentified, song)
            return song

        try:
            song = self._app.music_identifier.analyze_tempo_from_video(video_path)
        except Exception as err:
            song = SongMetadata(
                status=SongStatus.ERROR,
                provider="music_identifier",
                message=f"Error analyzing tempo: {err}",
            )

        self._events.emit(Event.SongIdentified, song)
        return song

    def _resolve_video_path(self, frames_folder_path: str) -> str | None:
        frames_folder = Path(frames_folder_path).expanduser().resolve()
        if not frames_folder.is_dir():
            return None

        for metadata_path in sorted(frames_folder.parent.glob("*.dance_tracker.json")):
            metadata = SequenceMetadataStore.read(str(metadata_path))
            if not metadata:
                continue

            frames_value = metadata.get("frames") or metadata.get("frames_path")
            resolved_frames = sequence_file_store.resolve_path(frames_value, metadata_path.parent)
            if resolved_frames != frames_folder:
                continue

            video_value = sequence_file_store.video_path_from_metadata(metadata)
            resolved_video = sequence_file_store.resolve_path(video_value, metadata_path.parent)
            if resolved_video and self._app.video_manager.is_video(str(resolved_video)):
                return str(resolved_video)

        return None


class SequencesAdapter:
    """Manages the in-memory sequence list and delegates all persistence to SequencePreferencesPort.

    Single source of truth for preferences is the injected port (PreferencesManager in
    the UI layer).  SequencesAdapter never reads or writes the preferences file directly.
    """

    def __init__(self, media: MediaAdapter, events: EventBus, prefs: SequencePreferencesPort):
        self._media = media
        self._events = events
        self._prefs = prefs
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

        folders = self._prefs.recent_folders()
        if dragged not in folders or target not in folders or dragged == target:
            return

        updated = [folder for folder in folders if folder != dragged]
        target_idx = updated.index(target)
        if drop_after:
            target_idx += 1
        updated.insert(target_idx, dragged)

        self._prefs.save_recent_folders_order(updated)
        self._emit_state()

    def remove(self, folder_path: str) -> None:
        normalized = self._normalize(folder_path)
        self._prefs.remove_recent_folder(normalized)
        if self._active_folder == normalized:
            self._active_folder = None
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
        return self._prefs.last_opened_folder()

    def thumbnail_path_for_folder(self, folder_path: str) -> str | None:
        return self._prefs.thumbnail_for_folder(self._normalize(folder_path))

    def _on_frames_loaded(self, path: str) -> None:
        normalized = self._normalize(path)
        self._prefs.register_recent_folder(normalized)
        self._active_folder = normalized
        self._emit_state()

    def _emit_state(self) -> None:
        items = [SequenceItem(folder_path=folder) for folder in self._prefs.recent_folders()]
        self._events.emit(
            Event.SequencesChanged,
            SequenceState(items=items, active_folder=self._active_folder),
        )

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
    def _normalize(path: str) -> str:
        return str(Path(path).expanduser())


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
    def __init__(self, events: EventBus):
        self._service: SequenceDataPort = SequenceDataService()
        self._events = events

    def read_video_data(self, frames_folder_path: str):
        return self._service.read_video_data(frames_folder_path)

    def read_bookmarks(self, frames_folder_path: str) -> list[Bookmark]:
        return self._service.read_bookmarks(frames_folder_path)

    def add_bookmark(self, frames_folder_path: str, frame: int) -> list[Bookmark]:
        result = self._service.add_bookmark(frames_folder_path, frame)
        self._events.emit(Event.BookmarksChanged, frames_folder_path)
        return result

    def move_bookmark(self, frames_folder_path: str, source_frame: int, target_frame: int) -> list[Bookmark]:
        result = self._service.move_bookmark(frames_folder_path, source_frame, target_frame)
        self._events.emit(Event.BookmarksChanged, frames_folder_path)
        return result

    def remove_bookmark(self, frames_folder_path: str, frame: int) -> list[Bookmark]:
        result = self._service.remove_bookmark(frames_folder_path, frame)
        self._events.emit(Event.BookmarksChanged, frames_folder_path)
        return result

    def set_bookmark_name(self, frames_folder_path: str, frame: int, name: str) -> list[Bookmark]:
        result = self._service.set_bookmark_name(frames_folder_path, frame, name)
        self._events.emit(Event.BookmarksChanged, frames_folder_path)
        return result

    def set_bookmark_locked(self, frames_folder_path: str, frame: int, locked: bool) -> list[Bookmark]:
        result = self._service.set_bookmark_locked(frames_folder_path, frame, locked)
        self._events.emit(Event.BookmarksChanged, frames_folder_path)
        return result

    def get_sequence_name(self, frames_folder_path: str) -> str | None:
        return self._service.get_sequence_name(frames_folder_path)

    def set_sequence_name(self, frames_folder_path: str, name: str) -> None:
        self._service.set_sequence_name(frames_folder_path, name)

    def previous_bookmark_frame(self, frames_folder_path: str, current_frame: int) -> int | None:
        return self._service.previous_bookmark_frame(frames_folder_path, current_frame)

    def next_bookmark_frame(self, frames_folder_path: str, current_frame: int) -> int | None:
        return self._service.next_bookmark_frame(frames_folder_path, current_frame)


class TrackDetectorAdapter:
    def __init__(self, app: DanceTrackerApp, events: EventBus):
        self._service = app.track_detector
        self._events = events

    def available_detectors(self) -> list[str]:
        return self._service.available_detectors()

    def active_detector(self) -> str:
        return self._service.active_detector()

    def set_active_detector(self, detector_name: str) -> bool:
        return self._service.set_active_detector(detector_name)

    def detect_people_for_sequence(self, frames_folder_path: str, frame_index: int | None = None) -> int:
        detected_frames = self._service.detect_people_for_sequence(frames_folder_path, frame_index=frame_index)
        self._events.emit(Event.DetectionsUpdated, frames_folder_path)
        return detected_frames

    def load_detections(self, frames_folder_path: str) -> None:
        self._service.load_detections(frames_folder_path)
        self._events.emit(Event.DetectionsUpdated, frames_folder_path)

    def detections_for_frame(self, frame_index: int) -> list[PersonDetection]:
        return self._service.detections_for_frame(frame_index)


class AppAdapter:
    def __init__(self, app: DanceTrackerApp, events: EventBus, prefs: SequencePreferencesPort):
        self.media = MediaAdapter(app, events)
        self.music: MusicPort = MusicAdapter(app, events)
        self.sequences = SequencesAdapter(self.media, events, prefs)
        self.frames = FramesAdapter(app)
        self.sequence_data = SequenceDataAdapter(events)
        self.track_detector = TrackDetectorAdapter(app, events)
