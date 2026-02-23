from PySide6.QtCore import QPoint, QMimeData, Qt
from PySide6.QtGui import QDrag, QMouseEvent
from PySide6.QtWidgets import QWidget, QSizePolicy

from ui.frames_mock import draw_thumbnail_frame


class ThumbnailWidget(QWidget):
    MIME_TYPE = "application/x-dance-layer-thumb"

    def __init__(self, label: str, seed: int = 1, parent=None):
        super().__init__(parent)
        self.label = label
        self.seed = seed
        self._drag_start_pos = QPoint()
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = ev.position().toPoint()
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev: QMouseEvent):
        if not (ev.buttons() & Qt.MouseButton.LeftButton):
            return

        distance = (ev.position().toPoint() - self._drag_start_pos).manhattanLength()
        if distance < 8:
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData(self.MIME_TYPE, f"{self.label}|{self.seed}".encode("utf-8"))
        drag.setMimeData(mime_data)
        drag.setPixmap(self.grab())
        drag.setHotSpot(ev.position().toPoint())
        drag.exec(Qt.DropAction.CopyAction)

    def paintEvent(self, ev):
        draw_thumbnail_frame(self, self.seed, self.label)
