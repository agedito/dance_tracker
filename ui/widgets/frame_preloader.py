import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage


class FramePreloader(QObject):
    frame_preloaded = Signal(int, bool, int)
    preload_finished = Signal(int)

    def __init__(self):
        super().__init__()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._generation = 0
        self._priority = 0
        self._lock = threading.Lock()
        self._full_images: list[QImage | None] = []
        self._loaded_flags: list[bool] = []

    @property
    def loaded_flags(self) -> list[bool]:
        with self._lock:
            return list(self._loaded_flags)

    @property
    def generation(self) -> int:
        return self._generation

    def get_image(self, idx: int) -> QImage | None:
        with self._lock:
            return self._full_images[idx] if idx < len(self._full_images) else None

    def set_priority(self, frame_idx: int) -> None:
        with self._lock:
            self._priority = frame_idx

    def start(self, frame_files: list[Path], bookmark_anchors: list[int]) -> None:
        if not frame_files:
            return

        self._stop.clear()
        self._generation += 1
        generation = self._generation
        total_frames = len(frame_files)

        with self._lock:
            self._full_images = [None] * total_frames
            self._loaded_flags = [False] * total_frames
            self._priority = 0

        anchors = [0, total_frames // 2, total_frames - 1, *bookmark_anchors]
        unique_anchors: list[int] = []
        for anchor in anchors:
            if 0 <= anchor < total_frames and anchor not in unique_anchors:
                unique_anchors.append(anchor)

        pending = set(range(total_frames))
        remaining_workers = len(unique_anchors)

        def preload_worker(anchor: int) -> None:
            nonlocal remaining_workers
            while True:
                if self._stop.is_set() or generation != self._generation:
                    return

                with self._lock:
                    if not pending:
                        break
                    idx = min(pending, key=lambda i: abs(i - anchor))
                    pending.remove(idx)

                image = QImage(str(frame_files[idx]))
                if self._stop.is_set() or generation != self._generation:
                    return

                if image.isNull():
                    self._safe_emit_preloaded(idx, False, generation)
                    continue

                with self._lock:
                    if idx >= len(self._full_images):
                        return
                    self._full_images[idx] = image
                    if idx < len(self._loaded_flags):
                        self._loaded_flags[idx] = True

                self._safe_emit_preloaded(idx, True, generation)

            should_emit_finished = False
            with self._lock:
                remaining_workers -= 1
                should_emit_finished = remaining_workers == 0

            if should_emit_finished and not self._stop.is_set() and generation == self._generation:
                try:
                    self.preload_finished.emit(generation)
                except RuntimeError:
                    return

        self._threads = []
        for anchor in unique_anchors:
            thread = threading.Thread(target=preload_worker, args=(anchor,), daemon=True)
            self._threads.append(thread)
            thread.start()

    def stop(self, wait: bool = False) -> None:
        self._stop.set()
        self._generation += 1
        threads = list(self._threads)
        self._threads = []
        if wait:
            for thread in threads:
                if thread.is_alive():
                    thread.join(timeout=0.5)

    def reset(self) -> None:
        with self._lock:
            self._full_images = []
            self._loaded_flags = []
            self._priority = 0

    def _safe_emit_preloaded(self, idx: int, loaded: bool, generation: int) -> None:
        try:
            self.frame_preloaded.emit(idx, loaded, generation)
        except RuntimeError:
            pass
