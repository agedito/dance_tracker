from PySide6.QtCore import QPoint, Qt, QMimeData
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QWidget, QSizePolicy

from ui.frames_mock import draw_thumbnail_frame


class ThumbnailWidget(QWidget):
    def __init__(self, label: str, seed: int = 1, parent=None):
        super().__init__(parent)
        self.label = label
        self.seed = seed
        self._drag_origin = QPoint()
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, ev):
        draw_thumbnail_frame(self, self.seed, self.label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.pos() - self._drag_origin).manhattanLength() < 8:
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData("application/x-layer-thumbnail", f"{self.label}||{self.seed}".encode())
        drag.setMimeData(mime)

        drag_pix = self.grab().scaled(
            max(1, self.width() // 2),
            max(1, self.height() // 2),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        drag.setPixmap(drag_pix)
        drag.setHotSpot(drag_pix.rect().center())
        drag.exec(Qt.DropAction.CopyAction)
