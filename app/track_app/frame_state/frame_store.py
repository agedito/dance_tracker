import re
from collections import OrderedDict
from pathlib import Path

from PySide6.QtGui import QPixmap


class FrameStore:
    VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}

    def __init__(self, cache_radius: int):
        self.cache_radius = cache_radius
        self._frame_files: list[Path] = []
        self._proxy_files: list[Path] = []
        self._cache: OrderedDict[tuple[bool, int], QPixmap] = OrderedDict()
        self._base_sizes: dict[int, tuple[int, int]] = {}

    @property
    def total_frames(self) -> int:
        return len(self._frame_files)

    @property
    def has_proxy_frames(self) -> bool:
        return bool(self._proxy_files)

    def load_folder(self, folder_path: str) -> int:
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            self._frame_files = []
            self._proxy_files = []
            self._cache.clear()
            self._base_sizes.clear()
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
        return len(files)

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

    @staticmethod
    def _natural_sort_key(path: Path):
        chunks = re.split(r"(\d+)", path.name.lower())
        return [int(chunk) if chunk.isdigit() else chunk for chunk in chunks]

    def get_frame(self, frame_idx: int, use_proxy: bool = False) -> QPixmap | None:
        if not self._frame_files or frame_idx < 0 or frame_idx >= len(self._frame_files):
            return None

        source_files = self._proxy_files if use_proxy and self._proxy_files else self._frame_files
        cache_key = (source_files is self._proxy_files, frame_idx)

        pix = self._cache.get(cache_key)
        if pix is None:
            pix = QPixmap(str(source_files[frame_idx]))
            if pix.isNull():
                return None

            self._cache[cache_key] = pix
            self._remember_base_size(frame_idx)
            self._enforce_cache_limit(center_frame=frame_idx)
        else:
            self._cache.move_to_end(cache_key)

        self._prefetch_neighbors(frame_idx, use_proxy=source_files is self._proxy_files)
        return pix

    def get_display_size(self, frame_idx: int) -> tuple[int, int] | None:
        if frame_idx in self._base_sizes:
            return self._base_sizes[frame_idx]

        if frame_idx < 0 or frame_idx >= len(self._frame_files):
            return None

        pix = self.get_frame(frame_idx, use_proxy=False)
        if pix is None:
            return None

        self._remember_base_size(frame_idx)
        return self._base_sizes.get(frame_idx)

    def _remember_base_size(self, frame_idx: int):
        if frame_idx in self._base_sizes or frame_idx < 0 or frame_idx >= len(self._frame_files):
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
            pix = QPixmap(str(source_files[idx]))
            if pix.isNull():
                continue
            self._cache[key] = pix
            if not source_key:
                self._base_sizes[idx] = (pix.width(), pix.height())

        self._enforce_cache_limit(center_frame)

    def _enforce_cache_limit(self, center_frame: int):
        max_items = (self.cache_radius * 2) + 1
        if self._proxy_files:
            max_items *= 2
        if max_items <= 0:
            self._cache.clear()
            return

        while len(self._cache) > max_items:
            farthest_idx = max(self._cache.keys(), key=lambda key: abs(key[1] - center_frame))
            self._cache.pop(farthest_idx, None)
