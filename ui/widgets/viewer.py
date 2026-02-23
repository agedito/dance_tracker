from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.frame_store import FrameStore
from ui.frames_mock import draw_viewer_frame
from utils.numbers import clamp


class ViewerWidget(QWidget):
    framesLoaded = Signal(int)

    def __init__(self, total_frames: int, frame_store: FrameStore, parent=None):
        super().__init__(parent)
        self.total_frames = total_frames
        self.frame = 0
        self.frame_store = frame_store
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAcceptDrops(True)

    def set_total_frames(self, total_frames: int):
        self.total_frames = max(1, total_frames)
        self.frame = clamp(self.frame, 0, self.total_frames - 1)
        self.update()

    def set_frame(self, f: int):
        self.frame = clamp(f, 0, self.total_frames - 1)
        self.update()

    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls() and any(url.isLocalFile() for url in ev.mimeData().urls()):
            ev.acceptProposedAction()
            return
        ev.ignore()

    def dropEvent(self, ev):
        for url in ev.mimeData().urls():
            if not url.isLocalFile():
                continue
            frame_count = self.frame_store.load_folder(url.toLocalFile())
            if frame_count > 0:
                self.framesLoaded.emit(frame_count)
                ev.acceptProposedAction()
                return
        ev.ignore()

    def paintEvent(self, ev):
        pixmap = self.frame_store.get_frame(self.frame)
        if pixmap is not None:
            painter = QPainter(self)
            painter.fillRect(self.rect(), Qt.GlobalColor.black)
            scaled = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.end()
            return

        draw_viewer_frame(self, self.frame, self.total_frames)
