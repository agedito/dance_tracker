from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class BeatMarkerWidget(QWidget):
    """Widget to show 8 musical pulses.    """

    beatChanged = Signal(object)

    def __init__(self, beats: int = 8, parent=None):
        super().__init__(parent)
        self.beats = max(1, beats)
        self._active_beat: int | None = None
        self.setMinimumHeight(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def active_beat(self) -> int | None:
        return self._active_beat

    def set_active_beat(self, beat: int | None):
        if beat is not None and (beat < 1 or beat > self.beats):
            return
        if self._active_beat == beat:
            return
        self._active_beat = beat
        self.update()
        self.beatChanged.emit(self._active_beat)

    def clear_active_beat(self):
        self.set_active_beat(None)

    def _slot_rect(self, idx: int) -> QRectF:
        spacing = 8
        total_spacing = spacing * (self.beats - 1)
        slot_w = max(28, (self.width() - total_spacing) // self.beats)
        x = idx * (slot_w + spacing)
        y = 2
        h = max(30, self.height() - 4)
        return QRectF(x, y, slot_w, h)

    def _beat_from_pos(self, x: float, y: float) -> int | None:
        for idx in range(self.beats):
            rect = self._slot_rect(idx)
            if rect.contains(x, y):
                return idx + 1
        return None

    def mousePressEvent(self, ev):
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        clicked = self._beat_from_pos(ev.position().x(), ev.position().y())
        if clicked is None:
            self.clear_active_beat()
            return

        if self._active_beat == clicked:
            self.clear_active_beat()
        else:
            self.set_active_beat(clicked)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        for idx in range(self.beats):
            beat = idx + 1
            rect = self._slot_rect(idx)

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(22, 27, 31))
            p.drawRoundedRect(rect, 8, 8)

            is_active = beat == self._active_beat
            if is_active:
                p.setPen(QPen(QColor(122, 162, 255, 220), 2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(rect.adjusted(4, 4, -4, -4))

            p.setPen(QColor(231, 237, 242) if is_active else QColor(167, 179, 189))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(beat))

        p.end()
