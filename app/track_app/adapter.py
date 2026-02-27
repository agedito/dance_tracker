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

        if self._app.video_manager.is_video(path):
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

            path = self._app.video_manager.extract_frames(
                path,
                on_progress=on_progress,
                should_cancel=should_cancel,
            )
            print("Video extracted at", path)

        if not path or not Path(path).is_dir():
            print("It's not a folder")
            return

        self._events.emit(Event.FramesLoaded, path)


class AppAdapter:
    def __init__(self, app: DanceTrackerApp, events: EventBus):
        self.media = MediaAdapter(app, events)
