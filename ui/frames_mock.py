import math

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter, QBrush, QRadialGradient, Qt, QLinearGradient, QFont, QPen
from PySide6.QtWidgets import QWidget

text_font = "Segoe UI"


def draw_ellipse(painter: QPainter, px: int, py: int, radius: int, alpha: int):
    rg = QRadialGradient(px, py, radius)
    rg.setColorAt(0.0, QColor(255, 255, 255, alpha))
    rg.setColorAt(1.0, QColor(255, 255, 255, 0))
    painter.setBrush(QBrush(rg))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(px - radius, py - radius, 2 * radius, 2 * radius)


def draw_thumbnail_frame(widget: QWidget, seed: int, label: str):
    p = QPainter(widget)
    rect = widget.rect()
    w, h = rect.width(), rect.height()

    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.fillRect(rect, QColor(12, 15, 18))
    g = QLinearGradient(0, 0, w, h)
    g.setColorAt(0.0, QColor(40 + (seed % 50), 70 + (seed % 80), 40 + (seed % 60), 235))
    g.setColorAt(1.0, QColor(110 + (seed % 60), 95 + (seed % 40), 30 + (seed % 30), 180))
    p.fillRect(rect, QBrush(g))

    for i in range(10):
        px = int((0.5 + 0.5 * math.sin((seed + i) * 3.1)) * w)
        py = int((0.5 + 0.5 * math.cos((seed + i) * 2.3)) * h)
        r = int((0.12 + (i % 4) * 0.05) * min(w, h))
        alpha = 16 + (i % 3) * 12
        draw_ellipse(p, px, py, r, alpha)

    p.setPen(QPen(QColor(255, 80, 80, 210), max(2, int(min(w, h) * 0.05))))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(int(w * 0.18), int(h * 0.65), int(w * 0.82), int(h * 0.55))

    p.setPen(QColor(255, 255, 255, 190))
    p.setFont(QFont(text_font, 9, QFont.Weight.DemiBold))
    p.drawText(10, 18, label)

    p.setPen(QPen(QColor(43, 52, 59), 1))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 8, 8)
    p.end()


def draw_viewer_frame(widget: QWidget, frame: int, total_frames: int, layer_label: str, layer_seed: int):
    import math
    w, h = widget.width(), widget.height()
    t = frame / max(1, (total_frames - 1))

    p = QPainter(widget)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.fillRect(widget.rect(), QColor(12, 14, 16))

    g = QLinearGradient(0, 0, w, h)
    g.setColorAt(
        0.0,
        QColor(20 + (layer_seed % 70), 30 + (layer_seed % 40), 25 + (layer_seed % 50), 240),
    )
    g.setColorAt(
        1.0,
        QColor(70 + (layer_seed % 90), 55 + (layer_seed % 80), 20 + (layer_seed % 45), 180),
    )
    p.fillRect(widget.rect(), QBrush(g))

    for i in range(18):
        px = int((0.5 + 0.5 * math.sin((i * 999) + t * 8.0 + layer_seed)) * w)
        py = int((0.5 + 0.5 * math.cos((i * 777) + t * 6.0 + layer_seed)) * h)
        r = int((0.05 + (i % 5) * 0.02) * min(w, h))
        alpha = 18 + (i % 4) * 6
        draw_ellipse(p, px, py, r, alpha)

    vg = QRadialGradient(int(w * 0.5), int(h * 0.55), int(min(w, h) * 0.75))
    vg.setColorAt(0.0, QColor(0, 0, 0, 0))
    vg.setColorAt(1.0, QColor(0, 0, 0, 160))
    p.fillRect(widget.rect(), QBrush(vg))

    p.setPen(QColor(255, 255, 255, 190))
    p.setFont(QFont(text_font, max(10, int(h * 0.05)), QFont.Weight.DemiBold))
    p.drawText(20, int(h * 0.15), f"Frame {frame}")

    p.setPen(QColor(255, 255, 255, 170))
    p.setFont(QFont(text_font, max(9, int(h * 0.035)), QFont.Weight.DemiBold))
    p.drawText(20, int(h * 0.23), layer_label)

    p.setFont(QFont(text_font, max(9, int(h * 0.04)), QFont.Weight.DemiBold))
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

    xph = int((frame / max(1, total_frames - 1)) * w)
    p.setPen(QPen(QColor(255, 80, 80, 230), 2))
    p.drawLine(xph, 0, xph, h)
    p.end()
