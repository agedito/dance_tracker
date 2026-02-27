from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.track_app.frame_state.layers import Segment
from utils.numbers import clamp


class TimelineTrack(QWidget):
    frameChanged = Signal(int)
    scrubStarted = Signal()
    scrubFinished = Signal()

    def __init__(self, total_frames: int, segments: list[Segment], parent=None):
        super().__init__(parent)
        self.total_frames = max(1, total_frames)
        self.segments = segments
        self.frame = 0
        self.loaded_flags = [False] * self.total_frames
        self.setFixedHeight(20)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _frame_from_pos(self, x: float) -> int:
        norm_x = clamp(int(x), 0, self.width())
        return int(round((norm_x / max(1, self.width())) * (self.total_frames - 1)))

    def set_total_frames(self, total_frames: int):
        self.total_frames = max(1, total_frames)
        self.frame = clamp(self.frame, 0, self.total_frames - 1)
        self.loaded_flags = [False] * self.total_frames
        self.update()

    def set_frame(self, f: int):
        self.frame = clamp(f, 0, self.total_frames - 1)
        self.update()

    def set_loaded_flags(self, flags: list[bool]):
        if len(flags) != self.total_frames:
            self.loaded_flags = (flags + [False] * self.total_frames)[:self.total_frames]
        else:
            self.loaded_flags = list(flags)
        self.update()

    def set_frame_loaded(self, frame: int, loaded: bool):
        if frame < 0 or frame >= self.total_frames:
            return
        self.loaded_flags[frame] = loaded
        self.update()

    def mousePressEvent(self, ev):
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        self.scrubStarted.emit()
        self.frameChanged.emit(self._frame_from_pos(ev.position().x()))

    def mouseMoveEvent(self, ev):
        if not (ev.buttons() & Qt.MouseButton.LeftButton):
            return
        self.frameChanged.emit(self._frame_from_pos(ev.position().x()))

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.scrubFinished.emit()
        super().mouseReleaseEvent(ev)

    def paintEvent(self, ev):
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        p.setBrush(QColor(12, 15, 18))
        p.setPen(QPen(QColor(43, 52, 59), 1))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 9, 9)

        self._draw_loaded_indicator(p, w, h)

        xph = int((self.frame / max(1, self.total_frames - 1)) * w)
        p.setPen(QPen(QColor(255, 80, 80, 240), 2))
        p.drawLine(xph, -4, xph, h + 4)
        p.end()

    def _draw_loaded_indicator(self, painter: QPainter, w: int, h: int):
        bar_h = 3
        y = h - bar_h - 1
        painter.setPen(Qt.PenStyle.NoPen)

        if w <= 1:
            color = QColor(42, 160, 88, 240) if self.loaded_flags and self.loaded_flags[0] else QColor(95, 98, 102, 200)
            painter.setBrush(color)
            painter.drawRect(QRectF(1, y, max(1, w - 2), bar_h))
            return

        for x in range(1, w - 1):
            frame = int((x / max(1, w - 1)) * (self.total_frames - 1))
            loaded = self.loaded_flags[frame] if frame < len(self.loaded_flags) else False
            color = QColor(42, 160, 88, 240) if loaded else QColor(95, 98, 102, 200)
            painter.setBrush(color)
            painter.drawRect(QRectF(x, y, 1, bar_h))
