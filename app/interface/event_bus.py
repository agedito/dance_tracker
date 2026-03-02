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
    """Decoupled event bus. Emitters and listeners don't know each other.

    Thread safety
    -------------
    A dispatcher can be injected via ``set_dispatcher``. Every callback is
    routed through it, allowing callers to marshal execution to a specific
    thread (e.g. the Qt main thread). When no dispatcher is set, callbacks
    are invoked synchronously on the calling thread.

    Re-entrancy
    -----------
    If ``emit`` is called while a previous ``emit`` is still executing on the
    same thread (i.e. a callback triggers a new event), the nested emission is
    deferred and processed after the current one finishes. This guarantees that
    all listeners for an event see a consistent state before any follow-on
    events fire.
    """

    def __init__(self):
        self._listeners: dict[Event, list[Callable[..., None]]] = defaultdict(list)
        self._lock = threading.Lock()
        self._local = threading.local()
        self._dispatcher: Callable[[Callable[[], None]], None] | None = None

    def set_dispatcher(self, dispatcher: Callable[[Callable[[], None]], None]) -> None:
        """Inject a function that schedules each callback invocation.

        The dispatcher receives a zero-argument callable and is responsible for
        calling it (e.g. by posting it to the Qt main-thread event queue).
        """
        self._dispatcher = dispatcher

    def on(self, event: Event, callback: Callable[..., None]) -> None:
        with self._lock:
            self._listeners[event].append(callback)

    def off(self, event: Event, callback: Callable[..., None]) -> None:
        with self._lock:
            listeners = self._listeners.get(event)
            if listeners and callback in listeners:
                listeners.remove(callback)

    def emit(self, event: Event, *args: Any) -> None:
        # Re-entrancy guard: if we're already inside an emit on this thread,
        # defer the new emission until the current one completes.
        if getattr(self._local, "depth", 0) > 0:
            if not hasattr(self._local, "deferred"):
                self._local.deferred = []
            self._local.deferred.append((event, args))
            return

        with self._lock:
            callbacks = list(self._listeners.get(event, []))

        self._local.depth = 1
        self._local.deferred = []
        try:
            for cb in callbacks:
                self._invoke(cb, args)

            # Drain deferred events (each drain round may itself enqueue more).
            while self._local.deferred:
                batch = self._local.deferred
                self._local.deferred = []
                for deferred_event, deferred_args in batch:
                    with self._lock:
                        deferred_cbs = list(self._listeners.get(deferred_event, []))
                    for cb in deferred_cbs:
                        self._invoke(cb, deferred_args)
        finally:
            self._local.depth = 0

    def _invoke(self, callback: Callable[..., None], args: tuple) -> None:
        if self._dispatcher:
            self._dispatcher(lambda cb=callback, a=args: cb(*a))
        else:
            callback(*args)

    def connect(self, listener: EventsListener) -> None:
        self.on(Event.FramesLoaded, listener.on_frames_loaded)
        self.on(Event.SongIdentified, listener.on_song_identified)
        self.on(Event.SequencesChanged, listener.on_sequences_changed)
        self.on(Event.DetectionsUpdated, listener.on_detections_updated)
        self.on(Event.BookmarksChanged, listener.on_bookmarks_changed)

    def disconnect(self, listener: EventsListener) -> None:
        self.off(Event.FramesLoaded, listener.on_frames_loaded)
        self.off(Event.SongIdentified, listener.on_song_identified)
        self.off(Event.SequencesChanged, listener.on_sequences_changed)
        self.off(Event.DetectionsUpdated, listener.on_detections_updated)
        self.off(Event.BookmarksChanged, listener.on_bookmarks_changed)
