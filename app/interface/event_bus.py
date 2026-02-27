from collections import defaultdict
from enum import Enum, auto
from typing import Any, Callable, Protocol

from app.interface.application import AppState
from app.interface.music import SongMetadata


class Event(Enum):
    FramesLoaded = auto()
    SongIdentified = auto()
    AppStateChanged = auto()
    LogMessage = auto()


class EventsListener(Protocol):
    def on_frames_loaded(self, path: str) -> None: ...

    def on_song_identified(self, song: SongMetadata) -> None: ...

    def on_app_state_changed(self, state: AppState) -> None: ...

    def on_log_message(self, message: str) -> None: ...


class EventBus:
    """Decoupled event bus. Emitters and listeners do not know each other."""

    def __init__(self):
        self._listeners: dict[Event, list[Callable[..., None]]] = defaultdict(list)

    def on(self, event: Event, callback: Callable[..., None]) -> None:
        self._listeners[event].append(callback)

    def off(self, event: Event, callback: Callable[..., None]) -> None:
        listeners = self._listeners.get(event)
        if listeners and callback in listeners:
            listeners.remove(callback)

    def emit(self, event: Event, *args: Any) -> None:
        for callback in self._listeners.get(event, []):
            callback(*args)

    def connect(self, listener: EventsListener) -> None:
        self.on(Event.FramesLoaded, listener.on_frames_loaded)
        self.on(Event.SongIdentified, listener.on_song_identified)
        self.on(Event.AppStateChanged, listener.on_app_state_changed)
        self.on(Event.LogMessage, listener.on_log_message)
