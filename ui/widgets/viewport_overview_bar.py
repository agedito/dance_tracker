from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class ViewportOverviewBar(QWidget):
    """Compact visual indicator of zoom (window width) and pan (window position)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._view_start = 0.0
        self._view_span = 1.0
        self.setFixedSize(140, 14)

    def set_viewport(self, start: float, span: float):
        clamped_span = max(0.01, min(1.0, span))
        clamped_start = max(0.0, min(1.0 - clamped_span, start))
        if abs(clamped_start - self._view_start) < 1e-9 and abs(clamped_span - self._view_span) < 1e-9:
            return
        self._view_start = clamped_start
        self._view_span = clamped_span
        self.update()

    def paintEvent(self, ev):
        _ = ev
        w = self.width()
        h = self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        border = QRectF(0.5, 0.5, w - 1, h - 1)
        p.setPen(QPen(QColor(68, 78, 86, 220), 1))
        p.setBrush(QColor(24, 30, 35, 220))
        p.drawRoundedRect(border, 4, 4)

        viewport_x = int(round(self._view_start * max(1, w - 2)))
        viewport_w = int(round(self._view_span * max(1, w - 2)))
        viewport_w = max(2, min(w - 2, viewport_w))
        viewport_x = max(1, min(w - viewport_w - 1, viewport_x + 1))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(69, 133, 255, 210))
        p.drawRoundedRect(QRectF(viewport_x, 1, viewport_w, h - 2), 3, 3)
        p.end()
