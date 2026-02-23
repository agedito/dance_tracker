import re
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.logic import clamp
from ui.frames_mock import draw_viewer_frame


class ViewerWidget(QWidget):
    frameFolderLoaded = Signal(int, str)

    def __init__(
        self,
        total_frames: int,
        cache_radius: int = 25,
        frame_cache_radius: int | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.total_frames = total_frames
        if frame_cache_radius is not None:
            cache_radius = frame_cache_radius
        self.cache_radius = max(0, cache_radius)
        self.frame = 0
        self.frame_paths: list[Path] = []
        self.cache: dict[int, QPixmap] = {}
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAcceptDrops(True)

    def set_frame(self, f: int):
        self.frame = clamp(f, 0, self.total_frames - 1)
        if self.frame_paths:
            self._update_cache_window(self.frame)
        self.update()

    def dragEnterEvent(self, ev):
        for url in ev.mimeData().urls():
            if Path(url.toLocalFile()).is_dir():
                ev.acceptProposedAction()
                return
        ev.ignore()

    def dropEvent(self, ev):
        for url in ev.mimeData().urls():
            folder = Path(url.toLocalFile())
            if folder.is_dir() and self.load_frame_folder(folder):
                ev.acceptProposedAction()
                return
        ev.ignore()

    def load_frame_folder(self, folder: Path) -> bool:
        frame_paths = sorted(
            [
                p
                for p in folder.iterdir()
                if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
            ],
            key=self._natural_key,
        )
        if not frame_paths:
            return False

        self.frame_paths = frame_paths
        self.total_frames = len(frame_paths)
        self.cache.clear()
        self.set_frame(0)
        self.frameFolderLoaded.emit(self.total_frames, str(folder))
        return True

    @staticmethod
    def _natural_key(path: Path):
        return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]

    def _update_cache_window(self, center_frame: int):
        start = max(0, center_frame - self.cache_radius)
        end = min(self.total_frames - 1, center_frame + self.cache_radius)
        keep = set(range(start, end + 1))

        for idx in list(self.cache):
            if idx not in keep:
                del self.cache[idx]

        for idx in keep:
            if idx not in self.cache:
                self.cache[idx] = QPixmap(str(self.frame_paths[idx]))

    def paintEvent(self, ev):
        if not self.frame_paths:
            draw_viewer_frame(self, self.frame, self.total_frames)
            return

        frame = self.cache.get(self.frame)
        if frame is None:
            self._update_cache_window(self.frame)
            frame = self.cache.get(self.frame)

        if frame is None or frame.isNull():
            draw_viewer_frame(self, self.frame, self.total_frames)
            return

        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        scaled = frame.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()
