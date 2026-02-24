import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class RadialMenuWidget(QWidget):
    """Transparent overlay that draws and handles a radial icon menu."""

    borderColorChanged = Signal(QColor)

    SYMBOLS = ["G", "V", "R", "A", "⏱", "↺", "★", "◎"]
    ICON_COUNT = 8
    RING_RADIUS = 102.0
    ICON_RADIUS = 20.0
    HUB_RADIUS = 28.0

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setMouseTracking(True)

        self._expanded = False
        self._rotation = 0.0
        self._selected = 0
        self._dragging = False
        self._last_drag_angle = 0.0
        self._anchor_rect: QRectF | None = None

        self._border_colors = {
            0: QColor(150, 150, 150),
            1: QColor(80, 200, 120),
            2: QColor(215, 84, 84),
            3: QColor(232, 206, 85),
        }
        self._active_color = self._border_colors[0]

    # ── Public API ───────────────────────────────────────────────────

    @property
    def active_border_color(self) -> QColor:
        return self._active_color

    def set_anchor_rect(self, rect: QRectF):
        """Set the video rect so the menu knows where to position itself."""
        self._anchor_rect = rect
        self.update()

    # ── Geometry helpers ─────────────────────────────────────────────

    def _center(self) -> QPointF:
        if self._anchor_rect:
            return QPointF(self._anchor_rect.right() - 38, self._anchor_rect.bottom() - 38)
        return QPointF(self.width() - 38, self.height() - 38)

    def _icon_centers(self, center: QPointF) -> list[QPointF]:
        step = (2 * math.pi) / self.ICON_COUNT
        return [
            QPointF(
                center.x() + math.cos(self._rotation + i * step) * self.RING_RADIUS,
                center.y() + math.sin(self._rotation + i * step) * self.RING_RADIUS,
            )
            for i in range(self.ICON_COUNT)
        ]

    @staticmethod
    def _in_circle(point: QPointF, center: QPointF, radius: float) -> bool:
        dx = point.x() - center.x()
        dy = point.y() - center.y()
        return (dx * dx + dy * dy) <= radius * radius

    @staticmethod
    def _angle_from(point: QPointF, center: QPointF) -> float:
        return math.atan2(point.y() - center.y(), point.x() - center.x())

    # ── Mouse events ─────────────────────────────────────────────────

    def mousePressEvent(self, ev):
        if ev.button() != Qt.MouseButton.LeftButton:
            ev.ignore()
            return

        center = self._center()
        pos = QPointF(ev.position())

        # Hub click → toggle
        if self._in_circle(pos, center, self.HUB_RADIUS):
            self._expanded = not self._expanded
            self._dragging = False
            self.update()
            ev.accept()
            return

        if self._expanded:
            # Icon click
            clip = self._anchor_rect or QRectF(self.rect())
            for idx, ic in enumerate(self._icon_centers(center)):
                if self._in_circle(pos, ic, self.ICON_RADIUS) and clip.contains(ic):
                    self._selected = idx
                    if idx in self._border_colors:
                        self._active_color = self._border_colors[idx]
                        self.borderColorChanged.emit(self._active_color)
                    self.update()
                    ev.accept()
                    return

            # Ring drag start
            dist = math.hypot(pos.x() - center.x(), pos.y() - center.y())
            if 32 <= dist <= 144:
                self._dragging = True
                self._last_drag_angle = self._angle_from(pos, center)
                ev.accept()
                return

        ev.ignore()

    def mouseMoveEvent(self, ev):
        if not self._expanded or not self._dragging:
            ev.ignore()
            return

        center = self._center()
        angle = self._angle_from(QPointF(ev.position()), center)
        self._rotation += angle - self._last_drag_angle
        self._last_drag_angle = angle
        self.update()
        ev.accept()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
        ev.ignore()

    # ── Painting ─────────────────────────────────────────────────────

    def paintEvent(self, ev):
        center = self._center()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self._expanded:
            self._paint_ring(painter, center)

        self._paint_hub(painter, center)
        painter.end()

    def _paint_ring(self, painter: QPainter, center: QPointF):
        painter.save()
        if self._anchor_rect:
            painter.setClipRect(self._anchor_rect)

        # Outer ring
        painter.setPen(QPen(QColor(116, 200, 255, 145), 2))
        painter.setBrush(QColor(22, 30, 38, 80))
        painter.drawEllipse(center, 103, 103)

        # Icons
        for idx, ic in enumerate(self._icon_centers(center)):
            is_sel = idx == self._selected
            bg = QColor(65, 122, 214, 220) if is_sel else QColor(27, 33, 42, 210)
            border = QColor(157, 210, 255, 240) if is_sel else QColor(120, 160, 190, 180)
            painter.setPen(QPen(border, 1.5))
            painter.setBrush(bg)
            painter.drawEllipse(ic, self.ICON_RADIUS, self.ICON_RADIUS)

            painter.setPen(QColor(239, 246, 255))
            text_rect = QRectF(ic.x() - 10, ic.y() - 10, 20, 20)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.SYMBOLS[idx])

        painter.restore()

    def _paint_hub(self, painter: QPainter, center: QPointF):
        painter.save()
        painter.setPen(QPen(QColor(170, 220, 255), 1.5))
        painter.setBrush(QColor(35, 52, 71, 225))
        painter.drawEllipse(center, self.HUB_RADIUS, self.HUB_RADIUS)

        painter.setPen(QColor(234, 247, 255))
        r = QRectF(center.x() - 15, center.y() - 15, 30, 30)
        symbol = "×" if self._expanded else "☰"
        painter.drawText(r, Qt.AlignmentFlag.AlignCenter, symbol)
        painter.restore()
