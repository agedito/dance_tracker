from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QWidget, QSizePolicy

from app.logic import clamp
from ui.frames_mock import build_thumbnail_pixmap, draw_viewer_frame


class ViewerWidget(QWidget):
    def __init__(self, total_frames: int, parent=None):
        super().__init__(parent)
        self.total_frames = total_frames
        self.frame = 0
        self.overlays = []
        self._overlay_drag_idx = None
        self._overlay_drag_delta = QPoint(0, 0)
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAcceptDrops(True)

    def set_frame(self, f: int):
        self.frame = clamp(f, 0, self.total_frames - 1)
        self.update()

    def paintEvent(self, ev):
        draw_viewer_frame(self, self.frame, self.total_frames)

        from PySide6.QtGui import QPainter

        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for item in self.overlays:
            target = QRect(item["pos"], item["pixmap"].size())
            qp.drawPixmap(target, item["pixmap"])
            qp.setPen(QPen(QColor(255, 255, 255, 140), 1))
            qp.drawRoundedRect(target.adjusted(0, 0, -1, -1), 6, 6)
        qp.end()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-layer-thumbnail"):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat("application/x-layer-thumbnail"):
            event.ignore()
            return
        raw = bytes(event.mimeData().data("application/x-layer-thumbnail")).decode(errors="ignore")
        label, seed_txt = raw.split("||", 1)
        seed = int(seed_txt)
        pix = build_thumbnail_pixmap(max(80, self.width() // 4), max(50, self.height() // 4), seed, label)
        pos = event.position().toPoint() - pix.rect().center()
        self.overlays.append({"pixmap": pix, "pos": self._clamp_pos(pos, pix.width(), pix.height())})
        self.update()
        event.acceptProposedAction()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        cursor = event.position().toPoint()
        for idx in range(len(self.overlays) - 1, -1, -1):
            item = self.overlays[idx]
            rect = QRect(item["pos"], item["pixmap"].size())
            if rect.contains(cursor):
                self._overlay_drag_idx = idx
                self._overlay_drag_delta = cursor - item["pos"]
                break
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._overlay_drag_idx is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        item = self.overlays[self._overlay_drag_idx]
        new_pos = event.position().toPoint() - self._overlay_drag_delta
        item["pos"] = self._clamp_pos(new_pos, item["pixmap"].width(), item["pixmap"].height())
        self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._overlay_drag_idx = None
        super().mouseReleaseEvent(event)

    def _clamp_pos(self, pos: QPoint, width: int, height: int) -> QPoint:
        x = clamp(pos.x(), 0, max(0, self.width() - width))
        y = clamp(pos.y(), 0, max(0, self.height() - height))
        return QPoint(x, y)
