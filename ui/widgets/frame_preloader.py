import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

from utils.frame_scheduler import FrameScheduler


class FramePreloader(QObject):
    frame_preloaded = Signal(int, bool, int)    # (frame_idx, loaded, generation)
    proxy_frame_preloaded = Signal(int, int)    # (frame_idx, generation)
    preload_finished = Signal(int)              # (generation)

    def __init__(self):
        super().__init__()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._generation = 0
        self._priority = 0
        self._lock = threading.Lock()
        self._full_images: list[QImage | None] = []
        self._proxy_images: list[QImage | None] = []
        self._loaded_flags: list[bool] = []
        self._proxy_loaded_flags: list[bool] = []

    # ── Properties ───────────────────────────────────────────────────

    @property
    def loaded_flags(self) -> list[bool]:
        with self._lock:
            return list(self._loaded_flags)

    @property
    def proxy_loaded_flags(self) -> list[bool]:
        with self._lock:
            return list(self._proxy_loaded_flags)

    @property
    def generation(self) -> int:
        return self._generation

    # ── Image access ─────────────────────────────────────────────────

    def get_image(self, idx: int) -> QImage | None:
        with self._lock:
            return self._full_images[idx] if idx < len(self._full_images) else None

    def get_proxy_image(self, idx: int) -> QImage | None:
        with self._lock:
            return self._proxy_images[idx] if idx < len(self._proxy_images) else None

    def set_priority(self, frame_idx: int) -> None:
        with self._lock:
            self._priority = frame_idx

    # ── Lifecycle ────────────────────────────────────────────────────

    def start(
        self,
        frame_files: list[Path],
        proxy_files: list[Path],
        bookmark_anchors: list[int],
    ) -> None:
        if not frame_files:
            return

        self._stop.clear()
        total_frames = len(frame_files)

        with self._lock:
            self._generation += 1
            generation = self._generation
            self._full_images = [None] * total_frames
            self._proxy_images = [None] * total_frames
            self._loaded_flags = [False] * total_frames
            self._proxy_loaded_flags = [False] * total_frames
            self._priority = 0

        # ── Full-res workers (anchor-based, parallel) ─────────────────
        unique_anchors = FrameScheduler.make_anchors(total_frames, bookmarks=bookmark_anchors)

        pending = set(range(total_frames))
        remaining_workers = len(unique_anchors)

        def full_worker(anchor: int) -> None:
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

        # ── Proxy worker (single thread, sequential from frame 0) ─────
        def proxy_worker() -> None:
            for idx, proxy_path in enumerate(proxy_files):
                if self._stop.is_set() or generation != self._generation:
                    return

                image = QImage(str(proxy_path))
                if self._stop.is_set() or generation != self._generation:
                    return

                with self._lock:
                    if idx >= len(self._proxy_images):
                        return
                    if not image.isNull():
                        self._proxy_images[idx] = image
                        if idx < len(self._proxy_loaded_flags):
                            self._proxy_loaded_flags[idx] = True

                self._safe_emit_proxy_preloaded(idx, generation)

        self._threads = []
        for anchor in unique_anchors:
            t = threading.Thread(target=full_worker, args=(anchor,), daemon=True)
            self._threads.append(t)
            t.start()

        if proxy_files and len(proxy_files) == total_frames:
            t = threading.Thread(target=proxy_worker, daemon=True)
            self._threads.append(t)
            t.start()

    def stop(self, wait: bool = False) -> None:
        self._stop.set()
        with self._lock:
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
            self._proxy_images = []
            self._loaded_flags = []
            self._proxy_loaded_flags = []
            self._priority = 0

    # ── Signal helpers ────────────────────────────────────────────────

    def _safe_emit_preloaded(self, idx: int, loaded: bool, generation: int) -> None:
        try:
            self.frame_preloaded.emit(idx, loaded, generation)
        except RuntimeError:
            pass

    def _safe_emit_proxy_preloaded(self, idx: int, generation: int) -> None:
        try:
            self.proxy_frame_preloaded.emit(idx, generation)
        except RuntimeError:
            pass
