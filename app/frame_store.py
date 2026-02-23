from collections import OrderedDict
from pathlib import Path
import re

from PySide6.QtGui import QPixmap


class FrameStore:
    VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

    def __init__(self, cache_radius: int):
        self.cache_radius = cache_radius
        self._frame_files: list[Path] = []
        self._cache: OrderedDict[int, QPixmap] = OrderedDict()

    @property
    def total_frames(self) -> int:
        return len(self._frame_files)

    def load_folder(self, folder_path: str) -> int:
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            self._frame_files = []
            self._cache.clear()
            return 0

        files = [
            p
            for p in sorted(folder.iterdir(), key=self._natural_sort_key)
            if p.is_file() and p.suffix.lower() in self.VALID_SUFFIXES
        ]
        self._frame_files = files
        self._cache.clear()
        return len(files)

    @staticmethod
    def _natural_sort_key(path: Path):
        chunks = re.split(r"(\d+)", path.name.lower())
        return [int(chunk) if chunk.isdigit() else chunk for chunk in chunks]

    def get_frame(self, frame_idx: int) -> QPixmap | None:
        if not self._frame_files or frame_idx < 0 or frame_idx >= len(self._frame_files):
            return None

        pix = self._cache.get(frame_idx)
        if pix is None:
            pix = QPixmap(str(self._frame_files[frame_idx]))
            if pix.isNull():
                return None
            self._cache[frame_idx] = pix
            self._enforce_cache_limit(center_frame=frame_idx)
        else:
            self._cache.move_to_end(frame_idx)

        self._prefetch_neighbors(frame_idx)
        return pix

    def _prefetch_neighbors(self, center_frame: int):
        for idx in range(
            max(0, center_frame - self.cache_radius),
            min(len(self._frame_files), center_frame + self.cache_radius + 1),
        ):
            if idx in self._cache:
                continue
            pix = QPixmap(str(self._frame_files[idx]))
            if pix.isNull():
                continue
            self._cache[idx] = pix

        self._enforce_cache_limit(center_frame)

    def _enforce_cache_limit(self, center_frame: int):
        max_items = (self.cache_radius * 2) + 1
        if max_items <= 0:
            self._cache.clear()
            return

        while len(self._cache) > max_items:
            farthest_idx = max(self._cache.keys(), key=lambda idx: abs(idx - center_frame))
            self._cache.pop(farthest_idx, None)
