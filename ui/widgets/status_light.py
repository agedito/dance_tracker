from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget


class StatusLight(QWidget):
    COLORS = {
        "gray": QColor(130, 130, 130),
        "red": QColor(231, 76, 60),
        "green": QColor(46, 204, 113),
        "yellow": QColor(241, 196, 15),
    }

    def __init__(self, status: str = "gray", diameter: int = 16, parent=None):
        super().__init__(parent)
        self._diameter = max(8, diameter)
        self._status = "gray"
        self.set_status(status)
        self.setFixedSize(self._diameter, self._diameter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setToolTip(self._status)

    @property
    def status(self) -> str:
        return self._status

    def set_status(self, status: str):
        normalized = status.lower().strip()
        if normalized not in self.COLORS:
            normalized = "gray"
        if self._status == normalized:
            return
        self._status = normalized
        self.setToolTip(self._status)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        color = self.COLORS[self._status]
        center = self.rect().center()
        radius = min(self.width(), self.height()) * 0.5 - 1

        painter.setPen(QPen(QColor(20, 20, 20, 190), 1))
        painter.setBrush(color)
        painter.drawEllipse(center, radius, radius)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 80))
        highlight_radius = max(2.0, radius * 0.45)
        painter.drawEllipse(
            center.x() - radius * 0.28,
            center.y() - radius * 0.28,
            highlight_radius,
            highlight_radius,
        )
        painter.end()
