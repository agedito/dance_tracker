import re
import threading
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage, QPixmap


class FrameStore(QObject):
    VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}

    frame_preloaded = Signal(int, bool, int)
    preload_finished = Signal(int)

    def __init__(self, cache_radius: int):
        super().__init__()
        self.cache_radius = cache_radius
        self._frame_files: list[Path] = []
        self._proxy_files: list[Path] = []
        self._cache: OrderedDict[tuple[bool, int], QPixmap] = OrderedDict()
        self._base_sizes: dict[int, tuple[int, int]] = {}
        self._proxy_cache_loaded = False

        self._full_images: list[QImage | None] = []
        self._loaded_flags: list[bool] = []

        self._preload_stop = threading.Event()
        self._preload_thread: threading.Thread | None = None
        self._preload_generation = 0
        self._preload_priority = 0
        self._lock = threading.Lock()

    @property
    def total_frames(self) -> int:
        return len(self._frame_files)

    @property
    def has_proxy_frames(self) -> bool:
        return bool(self._proxy_files)

    @property
    def loaded_flags(self) -> list[bool]:
        with self._lock:
            return list(self._loaded_flags)

    @property
    def preload_generation(self) -> int:
        return self._preload_generation

    def shutdown(self):
        self._stop_preload_thread(wait=True)

    def clear(self):
        self._stop_preload_thread(wait=True)
        self._frame_files = []
        self._proxy_files = []
        self._cache.clear()
        self._base_sizes.clear()
        self._proxy_cache_loaded = False
        with self._lock:
            self._full_images = []
            self._loaded_flags = []
            self._preload_priority = 0

    def load_folder(self, folder_path: str) -> int:
        self._stop_preload_thread(wait=True)

        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            self.clear()
            return 0

        files = [
            p
            for p in sorted(folder.iterdir(), key=self._natural_sort_key)
            if p.is_file() and p.suffix.lower() in self.VALID_SUFFIXES
        ]
        self._frame_files = files
        self._proxy_files = self._find_proxy_files(folder, len(files))
        self._cache.clear()
        self._base_sizes.clear()
        self._proxy_cache_loaded = False

        with self._lock:
            self._full_images = [None] * len(files)
            self._loaded_flags = [False] * len(files)
            self._preload_priority = 0

        self._preload_proxy_cache()
        self._start_full_preload_thread()
        return len(files)

    def request_preload_priority(self, frame_idx: int):
        if not self._frame_files:
            return
        target = max(0, min(frame_idx, len(self._frame_files) - 1))
        with self._lock:
            self._preload_priority = target

    def _find_proxy_files(self, folder: Path, expected_count: int) -> list[Path]:
        proxy_dir = folder.parent / "frames_mino"
        if not proxy_dir.exists() or not proxy_dir.is_dir():
            return []

        proxy_files = [
            p
            for p in sorted(proxy_dir.iterdir(), key=self._natural_sort_key)
            if p.is_file() and p.suffix.lower() in self.VALID_SUFFIXES
        ]
        if len(proxy_files) != expected_count:
            return []
        return proxy_files

    def _preload_proxy_cache(self):
        if not self._proxy_files or self._proxy_cache_loaded:
            return

        for idx, path in enumerate(self._proxy_files):
            pix = QPixmap(str(path))
            if pix.isNull():
                continue
            self._cache[(True, idx)] = pix

        self._proxy_cache_loaded = True

    def _start_full_preload_thread(self):
        if not self._frame_files:
            return

        self._preload_stop.clear()
        self._preload_generation += 1
        generation = self._preload_generation

        def preload_worker():
            pending = set(range(len(self._frame_files)))
            while pending:
                if self._preload_stop.is_set() or generation != self._preload_generation:
                    return

                with self._lock:
                    priority = self._preload_priority

                idx = min(pending, key=lambda i: abs(i - priority))
                pending.remove(idx)

                image = QImage(str(self._frame_files[idx]))
                if self._preload_stop.is_set() or generation != self._preload_generation:
                    return

                if image.isNull():
                    self._safe_emit_frame_preloaded(idx, False, generation)
                    continue

                with self._lock:
                    if idx >= len(self._full_images):
                        return
                    self._full_images[idx] = image
                    if idx < len(self._loaded_flags):
                        self._loaded_flags[idx] = True

                self._base_sizes[idx] = (image.width(), image.height())
                self._safe_emit_frame_preloaded(idx, True, generation)

            if not self._preload_stop.is_set() and generation == self._preload_generation:
                try:
                    self.preload_finished.emit(generation)
                except RuntimeError:
                    return

        self._preload_thread = threading.Thread(target=preload_worker, daemon=True)
        self._preload_thread.start()

    def _safe_emit_frame_preloaded(self, idx: int, loaded: bool, generation: int):
        try:
            self.frame_preloaded.emit(idx, loaded, generation)
        except RuntimeError:
            return

    def _stop_preload_thread(self, wait: bool = False):
        self._preload_stop.set()
        self._preload_generation += 1
        thread = self._preload_thread
        self._preload_thread = None
        if wait and thread and thread.is_alive():
            thread.join(timeout=0.5)

    @staticmethod
    def _natural_sort_key(path: Path):
        chunks = re.split(r"(\d+)", path.name.lower())
        return [int(chunk) if chunk.isdigit() else chunk for chunk in chunks]

    def get_frame(self, frame_idx: int, use_proxy: bool = False) -> QPixmap | None:
        if not self._frame_files or frame_idx < 0 or frame_idx >= len(self._frame_files):
            return None

        source_files = self._proxy_files if use_proxy and self._proxy_files else self._frame_files
        is_proxy = source_files is self._proxy_files
        cache_key = (is_proxy, frame_idx)

        pix = self._cache.get(cache_key)
        if pix is None:
            with self._lock:
                full_image = None
                if not is_proxy and frame_idx < len(self._full_images):
                    full_image = self._full_images[frame_idx]

            if full_image is not None:
                pix = QPixmap.fromImage(full_image)
            else:
                pix = QPixmap(str(source_files[frame_idx]))

            if pix.isNull():
                return None

            self._cache[cache_key] = pix
            self._remember_base_size(frame_idx)
            self._enforce_cache_limit(center_frame=frame_idx)
        else:
            self._cache.move_to_end(cache_key)

        self._prefetch_neighbors(frame_idx, use_proxy=is_proxy)
        return pix

    def get_display_size(self, frame_idx: int) -> tuple[int, int] | None:
        if frame_idx in self._base_sizes:
            return self._base_sizes[frame_idx]

        if frame_idx < 0 or frame_idx >= len(self._frame_files):
            return None

        with self._lock:
            image = self._full_images[frame_idx] if frame_idx < len(self._full_images) else None

        if image is not None:
            self._base_sizes[frame_idx] = (image.width(), image.height())
            return self._base_sizes[frame_idx]

        pix = self.get_frame(frame_idx, use_proxy=False)
        if pix is None:
            return None

        self._remember_base_size(frame_idx)
        return self._base_sizes.get(frame_idx)

    def _remember_base_size(self, frame_idx: int):
        if frame_idx in self._base_sizes or frame_idx < 0 or frame_idx >= len(self._frame_files):
            return

        with self._lock:
            image = self._full_images[frame_idx] if frame_idx < len(self._full_images) else None

        if image is not None:
            self._base_sizes[frame_idx] = (image.width(), image.height())
            return

        key = (False, frame_idx)
        base_pix = self._cache.get(key)
        if base_pix is None:
            base_pix = QPixmap(str(self._frame_files[frame_idx]))
            if base_pix.isNull():
                return
            self._cache[key] = base_pix

        self._base_sizes[frame_idx] = (base_pix.width(), base_pix.height())

    def _prefetch_neighbors(self, center_frame: int, use_proxy: bool):
        source_files = self._proxy_files if use_proxy and self._proxy_files else self._frame_files
        source_key = source_files is self._proxy_files
        for idx in range(
                max(0, center_frame - self.cache_radius),
                min(len(self._frame_files), center_frame + self.cache_radius + 1),
        ):
            key = (source_key, idx)
            if key in self._cache:
                continue

            with self._lock:
                image = self._full_images[idx] if (not source_key and idx < len(self._full_images)) else None

            if image is not None:
                pix = QPixmap.fromImage(image)
            else:
                pix = QPixmap(str(source_files[idx]))

            if pix.isNull():
                continue

            self._cache[key] = pix
            if not source_key:
                self._base_sizes[idx] = (pix.width(), pix.height())

        self._enforce_cache_limit(center_frame)

    def _enforce_cache_limit(self, center_frame: int):
        max_base_items = (self.cache_radius * 2) + 1
        if max_base_items <= 0:
            self._cache.clear()
            return

        while True:
            base_keys = [key for key in self._cache.keys() if not key[0]]
            if len(base_keys) <= max_base_items:
                break

            farthest_idx = max(base_keys, key=lambda key: abs(key[1] - center_frame))
            self._cache.pop(farthest_idx, None)
