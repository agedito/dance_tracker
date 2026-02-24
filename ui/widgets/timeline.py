from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.frame_state.layers import Segment
from utils.numbers import clamp


def status_color(t: str) -> QColor:
    if t == "ok":
        return QColor(46, 204, 113, 190)
    if t == "warn":
        return QColor(241, 196, 15, 200)
    if t == "err":
        return QColor(231, 76, 60, 220)
    return QColor(120, 120, 120, 180)


class TimelineTrack(QWidget):
    frameChanged = Signal(int)
    scrubStarted = Signal()
    scrubFinished = Signal()

    def __init__(self, total_frames: int, segments: list[Segment], parent=None):
        super().__init__(parent)
        self.total_frames = total_frames
        self.segments = segments
        self.frame = 0
        self.setFixedHeight(20)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _frame_from_pos(self, x: float) -> int:
        norm_x = clamp(x, 0, self.width())
        return int(round((norm_x / max(1, self.width())) * (self.total_frames - 1)))

    def set_total_frames(self, total_frames: int):
        self.total_frames = max(1, total_frames)
        self.frame = clamp(self.frame, 0, self.total_frames - 1)
        self.update()

    def set_frame(self, f: int):
        self.frame = clamp(f, 0, self.total_frames - 1)
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

        for s in self.segments:
            left = int((s.a / self.total_frames) * w)
            right = int((s.b / self.total_frames) * w)
            seg_w = max(1, right - left)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(status_color(s.t))
            p.drawRect(QRectF(left, 1, seg_w, h - 2))

        xph = int((self.frame / max(1, self.total_frames - 1)) * w)
        p.setPen(QPen(QColor(255, 80, 80, 240), 2))
        p.drawLine(xph, -4, xph, h + 4)
        p.end()
