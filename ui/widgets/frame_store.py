import re
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap

from ui.widgets.frame_preloader import FramePreloader
from ui.widgets.pixmap_cache import PixmapCache
from ui.widgets.sidecar_metadata_reader import SidecarMetadataReader

_VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def _scan_folder(folder: Path) -> list[Path]:
    return [
        p
        for p in sorted(folder.iterdir(), key=_natural_sort_key)
        if p.is_file() and p.suffix.lower() in _VALID_SUFFIXES
    ]


def _natural_sort_key(path: Path):
    chunks = re.split(r"(\d+)", path.name.lower())
    return [int(chunk) if chunk.isdigit() else chunk for chunk in chunks]


class FrameStore(QObject):
    VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}

    frame_preloaded = Signal(int, bool, int)
    preload_finished = Signal(int)

    def __init__(self, cache_radius: int):
        super().__init__()
        self._frame_files: list[Path] = []
        self._proxy_files: list[Path] = []
        self._metadata = SidecarMetadataReader()
        self._cache = PixmapCache(cache_radius)
        self._preloader = FramePreloader()
        self._preloader.frame_preloaded.connect(self.frame_preloaded)
        self._preloader.preload_finished.connect(self.preload_finished)

    @property
    def total_frames(self) -> int:
        return len(self._frame_files)

    @property
    def has_proxy_frames(self) -> bool:
        return bool(self._proxy_files)

    @property
    def loaded_flags(self) -> list[bool]:
        return self._preloader.loaded_flags

    @property
    def preload_generation(self) -> int:
        return self._preloader.generation

    def shutdown(self) -> None:
        self._preloader.stop(wait=True)

    def clear(self) -> None:
        self._preloader.stop(wait=True)
        self._frame_files = []
        self._proxy_files = []
        self._cache.clear()
        self._preloader.reset()

    def load_folder(self, folder_path: str) -> int:
        self._preloader.stop(wait=True)

        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            self.clear()
            return 0

        self._frame_files = _scan_folder(folder)
        self._proxy_files = self._metadata.find_proxy_files(folder, self._frame_files)
        self._cache.clear()
        bookmark_anchors = self._metadata.read_bookmark_anchor_frames(folder, len(self._frame_files))
        self._cache.preload_proxy(self._proxy_files)
        self._preloader.start(self._frame_files, bookmark_anchors)
        return len(self._frame_files)

    def request_preload_priority(self, frame_idx: int) -> None:
        if not self._frame_files:
            return
        target = max(0, min(frame_idx, len(self._frame_files) - 1))
        self._preloader.set_priority(target)

    def get_frame(self, frame_idx: int, use_proxy: bool = False) -> QPixmap | None:
        if not self._frame_files or frame_idx < 0 or frame_idx >= len(self._frame_files):
            return None
        return self._cache.get(
            frame_idx, use_proxy, self._frame_files, self._proxy_files, self._preloader.get_image
        )

    def get_display_size(self, frame_idx: int) -> tuple[int, int] | None:
        return self._cache.get_display_size(frame_idx, self._frame_files, self._preloader.get_image)
