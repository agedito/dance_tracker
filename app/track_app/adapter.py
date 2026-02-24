from pathlib import Path

from app.interface.application import MediaPort
from app.interface.event_bus import EventBus, Event
from app.track_app.main_app import DanceTrackerApp


class MediaAdapter(MediaPort):
    def __init__(self, app: DanceTrackerApp, events: EventBus):
        self._app = app
        self._events = events

    def load(self, path: str) -> None:
        print("Loading", path)

        if self._app.video_manager.is_video(path):
            path = self._app.video_manager.extract_frames(path)
            print("Video extracted at", path)

        if not Path(path).is_dir():
            print("It's not a folder")

        self._events.emit(Event.FramesLoaded, path)


class AppAdapter:
    def __init__(self, app: DanceTrackerApp, events: EventBus):
        self.media = MediaAdapter(app, events)
