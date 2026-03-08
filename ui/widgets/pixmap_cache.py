import re
from collections import OrderedDict
from pathlib import Path
from typing import Callable

from PySide6.QtGui import QImage, QPixmap

_VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def _natural_sort_key(path: Path):
    chunks = re.split(r"(\d+)", path.name.lower())
    return [int(chunk) if chunk.isdigit() else chunk for chunk in chunks]


class PixmapCache:
    def __init__(self, cache_radius: int):
        self._cache_radius = cache_radius
        self._cache: OrderedDict[tuple[bool, int], QPixmap] = OrderedDict()
        self._base_sizes: dict[int, tuple[int, int]] = {}

    def clear(self) -> None:
        self._cache.clear()
        self._base_sizes.clear()

    def get(
        self,
        frame_idx: int,
        use_proxy: bool,
        frame_files: list[Path],
        proxy_files: list[Path],
        get_full_image: Callable[[int], QImage | None],
        get_proxy_image: Callable[[int], QImage | None] | None = None,
    ) -> QPixmap | None:
        source_files = proxy_files if use_proxy and proxy_files else frame_files
        is_proxy = source_files is proxy_files
        cache_key = (is_proxy, frame_idx)

        pix = self._cache.get(cache_key)
        if pix is None:
            if is_proxy:
                image = get_proxy_image(frame_idx) if get_proxy_image else None
            else:
                image = get_full_image(frame_idx)

            if image is not None:
                pix = QPixmap.fromImage(image)
            else:
                pix = QPixmap(str(source_files[frame_idx]))

            if pix.isNull():
                return None

            self._cache[cache_key] = pix
            self._remember_base_size(frame_idx, is_proxy, pix, get_full_image, frame_files)
            self._enforce_limit(frame_idx)
        else:
            self._cache.move_to_end(cache_key)

        self._prefetch_neighbors(
            frame_idx, is_proxy, frame_files, proxy_files, get_full_image, get_proxy_image
        )
        return pix

    def get_display_size(
        self,
        frame_idx: int,
        frame_files: list[Path],
        get_full_image: Callable[[int], QImage | None],
    ) -> tuple[int, int] | None:
        if frame_idx in self._base_sizes:
            return self._base_sizes[frame_idx]

        if frame_idx < 0 or frame_idx >= len(frame_files):
            return None

        image = get_full_image(frame_idx)
        if image is not None:
            self._base_sizes[frame_idx] = (image.width(), image.height())
            return self._base_sizes[frame_idx]

        pix = self.get(frame_idx, False, frame_files, [], get_full_image)
        if pix is None:
            return None
        return self._base_sizes.get(frame_idx)

    def _remember_base_size(
        self,
        frame_idx: int,
        is_proxy: bool,
        pix: QPixmap,
        get_full_image: Callable[[int], QImage | None],
        frame_files: list[Path],
    ) -> None:
        if is_proxy or frame_idx in self._base_sizes or frame_idx < 0 or frame_idx >= len(frame_files):
            return
        image = get_full_image(frame_idx)
        if image is not None:
            self._base_sizes[frame_idx] = (image.width(), image.height())
        else:
            self._base_sizes[frame_idx] = (pix.width(), pix.height())

    def _prefetch_neighbors(
        self,
        center_frame: int,
        is_proxy: bool,
        frame_files: list[Path],
        proxy_files: list[Path],
        get_full_image: Callable[[int], QImage | None],
        get_proxy_image: Callable[[int], QImage | None] | None = None,
    ) -> None:
        source_files = proxy_files if is_proxy else frame_files
        for idx in range(
            max(0, center_frame - self._cache_radius),
            min(len(frame_files), center_frame + self._cache_radius + 1),
        ):
            key = (is_proxy, idx)
            if key in self._cache:
                continue

            if is_proxy:
                image = get_proxy_image(idx) if get_proxy_image else None
            else:
                image = get_full_image(idx)
            if image is not None:
                pix = QPixmap.fromImage(image)
            else:
                pix = QPixmap(str(source_files[idx]))

            if pix.isNull():
                continue

            self._cache[key] = pix
            if not is_proxy:
                self._base_sizes[idx] = (pix.width(), pix.height())

        self._enforce_limit(center_frame)

    def _enforce_limit(self, center_frame: int) -> None:
        max_base_items = (self._cache_radius * 2) + 1
        if max_base_items <= 0:
            self._cache.clear()
            return

        while True:
            base_keys = [key for key in self._cache.keys() if not key[0]]
            if len(base_keys) <= max_base_items:
                break
            farthest_idx = max(base_keys, key=lambda key: abs(key[1] - center_frame))
            self._cache.pop(farthest_idx, None)
