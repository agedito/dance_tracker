import threading
from collections import defaultdict
from enum import Enum, auto
from typing import Any, Callable, Protocol

from app.interface.music import SongMetadata
from app.interface.sequences import SequenceState


class Event(Enum):
    FramesLoaded = auto()
    SongIdentified = auto()
    SequencesChanged = auto()
    DetectionsUpdated = auto()
    BookmarksChanged = auto()


class EventsListener(Protocol):
    def on_frames_loaded(self, path: str) -> None: ...

    def on_song_identified(self, song: SongMetadata) -> None: ...

    def on_sequences_changed(self, state: "SequenceState") -> None: ...

    def on_detections_updated(self, frames_folder_path: str) -> None: ...

    def on_bookmarks_changed(self, frames_folder_path: str) -> None: ...


class EventBus:
    """Decoupled event bus. Emitters and listeners don't know each other."""

    def __init__(self):
        self._listeners: dict[Event, list[Callable[..., None]]] = defaultdict(list)
        self._lock = threading.Lock()

    def on(self, event: Event, callback: Callable[..., None]) -> None:
        with self._lock:
            self._listeners[event].append(callback)

    def off(self, event: Event, callback: Callable[..., None]) -> None:
        with self._lock:
            listeners = self._listeners.get(event)
            if listeners and callback in listeners:
                listeners.remove(callback)

    def emit(self, event: Event, *args: Any) -> None:
        with self._lock:
            callbacks = list(self._listeners.get(event, []))
        for callback in callbacks:
            callback(*args)

    def connect(self, listener: EventsListener) -> None:
        self.on(Event.FramesLoaded, listener.on_frames_loaded)
        self.on(Event.SongIdentified, listener.on_song_identified)
        self.on(Event.SequencesChanged, listener.on_sequences_changed)
        self.on(Event.DetectionsUpdated, listener.on_detections_updated)
        self.on(Event.BookmarksChanged, listener.on_bookmarks_changed)
