from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from utils.numbers import clamp


class ViewportOverviewBar(QWidget):
    """Compact visual indicator of zoom (window width) and pan (window position)."""

    viewportChangeRequested = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._view_start = 0.0
        self._view_span = 1.0
        self._dragging = False
        self._drag_offset = 0.0
        self.setFixedSize(140, 14)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def set_viewport(self, start: float, span: float):
        clamped_span = max(0.01, min(1.0, span))
        clamped_start = max(0.0, min(1.0 - clamped_span, start))
        if abs(clamped_start - self._view_start) < 1e-9 and abs(clamped_span - self._view_span) < 1e-9:
            return
        self._view_start = clamped_start
        self._view_span = clamped_span
        self.update()

    def mousePressEvent(self, ev):
        if ev.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(ev)
            return

        track_width = max(1.0, float(self.width() - 2))
        viewport_px = self._view_span * track_width
        viewport_left = self._view_start * track_width
        click_x = clamp(ev.position().x() - 1.0, 0.0, track_width)

        if viewport_left <= click_x <= viewport_left + viewport_px:
            self._dragging = True
            self._drag_offset = click_x - viewport_left
        else:
            centered = (click_x / track_width) - (self._view_span / 2.0)
            self.viewportChangeRequested.emit(clamp(centered, 0.0, 1.0 - self._view_span), self._view_span)
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        ev.accept()

    def mouseMoveEvent(self, ev):
        if not self._dragging:
            super().mouseMoveEvent(ev)
            return

        track_width = max(1.0, float(self.width() - 2))
        click_x = clamp(ev.position().x() - 1.0, 0.0, track_width)
        proposed = (click_x - self._drag_offset) / track_width
        self.viewportChangeRequested.emit(clamp(proposed, 0.0, 1.0 - self._view_span), self._view_span)
        ev.accept()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            ev.accept()
            return
        super().mouseReleaseEvent(ev)

    def wheelEvent(self, ev):
        delta_y = ev.angleDelta().y()
        if delta_y == 0:
            ev.ignore()
            return

        anchor = clamp((ev.position().x() - 1.0) / max(1.0, float(self.width() - 2)), 0.0, 1.0)
        anchor_frame = self._view_start + anchor * self._view_span
        factor = 0.84 if delta_y > 0 else 1.19
        next_span = clamp(self._view_span * factor, 0.01, 1.0)
        next_start = clamp(anchor_frame - anchor * next_span, 0.0, 1.0 - next_span)
        self.viewportChangeRequested.emit(next_start, next_span)
        ev.accept()

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
