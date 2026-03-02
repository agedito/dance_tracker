from typing import Callable

from ui.widgets.frame_store import FrameStore


class PreloadTracker:
    """Tracks per-frame preload progress from FrameStore signals."""

    def __init__(
        self,
        frame_store: FrameStore,
        on_frame_loaded: Callable[[int, bool, int, bool], None],
        on_finished: Callable[[int, bool], None],
    ):
        self._frame_store = frame_store
        self._on_frame_loaded = on_frame_loaded
        self._on_finished = on_finished
        self._loaded_frames: set[int] = set()
        self._total_frames = 0
        self._active_generation = 0
        self._preload_done = False

    @property
    def loaded_count(self) -> int:
        return min(self._total_frames, len(self._loaded_frames))

    @property
    def preload_done(self) -> bool:
        return self._preload_done

    def reset(self, total_frames: int, generation: int, loaded_flags: list[bool]) -> None:
        self._total_frames = total_frames
        self._active_generation = generation
        self._loaded_frames = {i for i, f in enumerate(loaded_flags) if f}
        self._preload_done = self.loaded_count >= total_frames

    def on_frame_preloaded(self, frame: int, loaded: bool, generation: int) -> None:
        if generation != self._active_generation:
            return
        if frame < 0 or frame >= self._total_frames:
            return
        if loaded:
            self._loaded_frames.add(frame)
        else:
            self._loaded_frames.discard(frame)
        flags = self._frame_store.loaded_flags
        self._loaded_frames = {i for i, is_loaded in enumerate(flags) if is_loaded}
        self._on_frame_loaded(frame, loaded, self.loaded_count, self._preload_done)

    def on_preload_finished(self, generation: int) -> None:
        if generation != self._active_generation:
            return
        self._preload_done = True
        self._on_finished(self.loaded_count, True)
