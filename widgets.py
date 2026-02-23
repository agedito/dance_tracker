from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient
from PySide6.QtWidgets import QWidget, QSizePolicy

from app_logic import Segment, clamp


def status_color(t: str) -> QColor:
    if t == "ok":
        return QColor(46, 204, 113, 190)
    if t == "warn":
        return QColor(241, 196, 15, 200)
    if t == "err":
        return QColor(231, 76, 60, 220)
    return QColor(120, 120, 120, 180)


class ViewerWidget(QWidget):
    def __init__(self, total_frames: int, parent=None):
        super().__init__(parent)
        self.total_frames = total_frames
        self.frame = 0
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_frame(self, f: int):
        self.frame = clamp(f, 0, self.total_frames - 1)
        self.update()

    def paintEvent(self, ev):
        import math
        w, h = self.width(), self.height()
        f = self.frame
        t = f / max(1, (self.total_frames - 1))

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor(12, 14, 16))

        g = QLinearGradient(0, 0, w, h)
        g.setColorAt(0.0, QColor(20, 45, 25, 240))
        g.setColorAt(1.0, QColor(80, 70, 20, 180))
        p.fillRect(self.rect(), QBrush(g))

        for i in range(18):
            px = int((0.5 + 0.5 * math.sin((i * 999) + t * 8.0)) * w)
            py = int((0.5 + 0.5 * math.cos((i * 777) + t * 6.0)) * h)
            r = int((0.05 + (i % 5) * 0.02) * min(w, h))
            rg = QRadialGradient(px, py, r)
            alpha = 18 + (i % 4) * 6
            rg.setColorAt(0.0, QColor(255, 255, 255, alpha))
            rg.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setBrush(QBrush(rg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(px - r, py - r, 2 * r, 2 * r)

        vg = QRadialGradient(int(w * 0.5), int(h * 0.55), int(min(w, h) * 0.75))
        vg.setColorAt(0.0, QColor(0, 0, 0, 0))
        vg.setColorAt(1.0, QColor(0, 0, 0, 160))
        p.fillRect(self.rect(), QBrush(vg))

        p.setPen(QColor(255, 255, 255, 190))
        p.setFont(QFont("Segoe UI", max(10, int(h * 0.05)), QFont.Weight.DemiBold))
        p.drawText(20, int(h * 0.15), f"Frame {f}")

        p.setFont(QFont("Segoe UI", max(9, int(h * 0.04)), QFont.Weight.DemiBold))
        p.setPen(QColor(255, 255, 255, 170))
        wm_text = "NATIONAL GEOGRAPHIC"
        text_w = p.fontMetrics().horizontalAdvance(wm_text)
        x = w - text_w - 20
        y = h - 18
        p.setPen(QPen(QColor(255, 210, 74), 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(x - 28, y - 14, 18, 18)
        p.setPen(QColor(255, 255, 255, 170))
        p.drawText(x, y, wm_text)

        xph = int((f / max(1, self.total_frames - 1)) * w)
        p.setPen(QPen(QColor(255, 80, 80, 230), 2))
        p.drawLine(xph, 0, xph, h)
        p.end()


class ThumbnailWidget(QWidget):
    def __init__(self, label: str, seed: int = 1, parent=None):
        super().__init__(parent)
        self.label = label
        self.seed = seed
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, ev):
        import math
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        p.fillRect(self.rect(), QColor(12, 15, 18))
        g = QLinearGradient(0, 0, w, h)
        g.setColorAt(0.0, QColor(40 + (self.seed % 50), 70 + (self.seed % 80), 40 + (self.seed % 60), 235))
        g.setColorAt(1.0, QColor(110 + (self.seed % 60), 95 + (self.seed % 40), 30 + (self.seed % 30), 180))
        p.fillRect(self.rect(), QBrush(g))

        for i in range(10):
            px = int((0.5 + 0.5 * math.sin((self.seed + i) * 3.1)) * w)
            py = int((0.5 + 0.5 * math.cos((self.seed + i) * 2.3)) * h)
            r = int((0.12 + (i % 4) * 0.05) * min(w, h))
            rg = QRadialGradient(px, py, r)
            alpha = 16 + (i % 3) * 12
            rg.setColorAt(0.0, QColor(255, 255, 255, alpha))
            rg.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setBrush(QBrush(rg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(px - r, py - r, 2 * r, 2 * r)

        p.setPen(QPen(QColor(255, 80, 80, 210), max(2, int(min(w, h) * 0.05))))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(int(w * 0.18), int(h * 0.65), int(w * 0.82), int(h * 0.55))

        p.setPen(QColor(255, 255, 255, 190))
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        p.drawText(10, 18, self.label)

        p.setPen(QPen(QColor(43, 52, 59), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 8, 8)
        p.end()


class TimelineTrack(QWidget):
    frameChanged = Signal(int)

    def __init__(self, total_frames: int, segments: list[Segment], parent=None):
        super().__init__(parent)
        self.total_frames = total_frames
        self.segments = segments
        self.frame = 0
        self.setFixedHeight(20)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_frame(self, f: int):
        self.frame = clamp(f, 0, self.total_frames - 1)
        self.update()

    def mousePressEvent(self, ev):
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        x = clamp(ev.position().x(), 0, self.width())
        f = int(round((x / max(1, self.width())) * (self.total_frames - 1)))
        self.frameChanged.emit(f)

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
