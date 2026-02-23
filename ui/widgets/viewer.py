from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient
from PySide6.QtWidgets import QWidget, QSizePolicy

from app_logic import clamp


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
