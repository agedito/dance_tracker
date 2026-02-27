from pathlib import Path
from collections.abc import Callable

from app.interface.event_bus import EventBus, Event
from app.interface.music import SongMetadata, SongStatus
from app.track_app.main_app import DanceTrackerApp


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
        except Exception as err:  # Defensive: never break media load on music service errors.
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


class AppAdapter:
    def __init__(self, app: DanceTrackerApp, events: EventBus):
        self.media = MediaAdapter(app, events)
