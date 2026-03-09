"""Small navigation button strip for a timeline track.

Four buttons:
  ◀· prev frame WITHOUT data (gap)
  ◀● prev frame WITH data
  ●▶ next frame WITH data
  ·▶ next frame WITHOUT data (gap)
"""

from collections.abc import Callable

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QWidget

_BTN = 18   # button size px
_DOT = 5    # dot radius px


def _make_icon(arrow_left: bool, has_data: bool, dot_color: QColor) -> QIcon:
    w, h = 22, _BTN
    px = QPixmap(w, h)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    gray   = QColor(100, 105, 112, 200)
    active = dot_color if has_data else QColor(100, 105, 112, 140)

    # Arrow triangle
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(gray)
    mid_y = h / 2.0
    tip   = 5.0
    base  = 11.0
    half  = 4.5
    if arrow_left:
        pts = [(tip, mid_y), (base, mid_y - half), (base, mid_y + half)]
    else:
        pts = [(w - tip, mid_y), (w - base, mid_y - half), (w - base, mid_y + half)]
    p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in pts]))

    # Dot — filled circle (has data) or hollow ring (gap)
    dot_x = float(w - 8) if arrow_left else 8.0
    r = float(_DOT - (0 if has_data else 1))
    if has_data:
        p.setBrush(active)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(dot_x, mid_y), r, r)
    else:
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(active, 1.5))
        p.drawEllipse(QPointF(dot_x, mid_y), r, r)

    p.end()
    return QIcon(px)


_BTN_STYLE = (
    "QToolButton {"
    "  background: transparent; border: none; border-radius: 4px; padding: 0px;"
    "}"
    "QToolButton:hover { background: rgba(255,255,255,20); }"
    "QToolButton:pressed { background: rgba(255,255,255,10); }"
)


class TrackNavButtons(QWidget):
    """Four small navigation buttons: ◀· ◀● ●▶ ·▶"""

    def __init__(
        self,
        dot_color: QColor,
        on_prev_gap: Callable[[], None],
        on_prev_data: Callable[[], None],
        on_next_data: Callable[[], None],
        on_next_gap: Callable[[], None],
        parent=None,
    ) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        defs = [
            (True,  False, on_prev_gap,  "Previous frame without data"),
            (True,  True,  on_prev_data, "Previous frame with data"),
            (False, True,  on_next_data, "Next frame with data"),
            (False, False, on_next_gap,  "Next frame without data"),
        ]
        for left, data, cb, tip in defs:
            btn = QToolButton()
            btn.setIcon(_make_icon(left, data, dot_color))
            btn.setIconSize(QSize(22, _BTN))
            btn.setFixedSize(24, _BTN + 4)
            btn.setToolTip(tip)
            btn.setStyleSheet(_BTN_STYLE)
            btn.clicked.connect(cb)
            layout.addWidget(btn)

        self.setFixedSize(4 * 25, _BTN + 4)
