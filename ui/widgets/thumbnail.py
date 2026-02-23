from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient
from PySide6.QtWidgets import QWidget, QSizePolicy


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
