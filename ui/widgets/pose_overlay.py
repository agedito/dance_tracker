"""Pose overlay widget: toggle button + skeleton drawing on the viewer."""

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QWidget

# MediaPipe 33-landmark skeleton connections (landmark index pairs)
_POSE_CONNECTIONS = [
    # Face
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    # Shoulders
    (11, 12),
    # Left arm
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    # Right arm
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    # Torso
    (11, 23), (12, 24), (23, 24),
    # Left leg
    (23, 25), (25, 27), (27, 29), (27, 31), (29, 31),
    # Right leg
    (24, 26), (26, 28), (28, 30), (28, 32), (30, 32),
]

_LEFT_LANDMARKS = {1, 2, 3, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31}
_RIGHT_LANDMARKS = {4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32}

_COLOR_LEFT = QColor(130, 80, 255, 210)   # violet
_COLOR_RIGHT = QColor(255, 80, 160, 210)  # pink
_COLOR_MID = QColor(200, 180, 255, 200)   # light violet
_POINT_RADIUS = 3.0
_VISIBILITY_THRESHOLD = 0.5


def _landmark_color(index: int) -> QColor:
    if index in _LEFT_LANDMARKS:
        return _COLOR_LEFT
    if index in _RIGHT_LANDMARKS:
        return _COLOR_RIGHT
    return _COLOR_MID


def _connection_color(a: int, b: int) -> QColor:
    if a in _LEFT_LANDMARKS and b in _LEFT_LANDMARKS:
        return _COLOR_LEFT
    if a in _RIGHT_LANDMARKS and b in _RIGHT_LANDMARKS:
        return _COLOR_RIGHT
    return _COLOR_MID


class PoseOverlay(QWidget):
    """Toggle button + skeleton drawing for detected poses."""

    repaintRequested = Signal()

    def __init__(self, pose_detector, parent: QWidget) -> None:
        super().__init__(parent)
        self._pose_detector = pose_detector
        self._show = True

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "background-color: rgba(70, 70, 70, 150); border-radius: 12px;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        button = QToolButton(self)
        button.setCheckable(True)
        button.setChecked(True)
        button.setText("🤸")
        button.setToolTip("Show or hide pose skeleton")
        button.setStyleSheet(
            "QToolButton {"
            "color: white;"
            "font-size: 15px;"
            "background: transparent;"
            "border: none;"
            "padding: 2px 4px;"
            "}"
            "QToolButton:checked { color: #B45DFF; }"
        )
        button.toggled.connect(self._on_toggled)
        layout.addWidget(button)
        self.adjustSize()

    def reposition(self, video_rect: QRectF, y_offset: int = 0) -> None:
        self.adjustSize()
        size = self.sizeHint()
        margin = 10
        x = int(video_rect.right() - size.width() - margin)
        y = y_offset if y_offset > 0 else int(video_rect.top() + margin)
        self.setGeometry(x, y, size.width(), size.height())
        self.raise_()

    def paint(self, painter: QPainter, video_rect: QRectF, frame: int) -> None:
        if not self._show:
            return
        poses = self._pose_detector.poses_for_frame(frame)
        if not poses:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        for pose in poses:
            lm_map = {lm.index: lm for lm in pose.landmarks}

            # Draw connections
            for a_idx, b_idx in _POSE_CONNECTIONS:
                a = lm_map.get(a_idx)
                b = lm_map.get(b_idx)
                if a is None or b is None:
                    continue
                if a.visibility < _VISIBILITY_THRESHOLD or b.visibility < _VISIBILITY_THRESHOLD:
                    continue
                ax = video_rect.x() + a.x * video_rect.width()
                ay = video_rect.y() + a.y * video_rect.height()
                bx = video_rect.x() + b.x * video_rect.width()
                by = video_rect.y() + b.y * video_rect.height()
                color = _connection_color(a_idx, b_idx)
                painter.setPen(QPen(color, 1.5))
                painter.drawLine(int(ax), int(ay), int(bx), int(by))

            # Draw landmark points
            painter.setPen(Qt.PenStyle.NoPen)
            for lm in pose.landmarks:
                if lm.visibility < _VISIBILITY_THRESHOLD:
                    continue
                lx = video_rect.x() + lm.x * video_rect.width()
                ly = video_rect.y() + lm.y * video_rect.height()
                painter.setBrush(_landmark_color(lm.index))
                painter.drawEllipse(
                    QRectF(lx - _POINT_RADIUS, ly - _POINT_RADIUS,
                           _POINT_RADIUS * 2, _POINT_RADIUS * 2)
                )

        painter.restore()

    def _on_toggled(self, checked: bool) -> None:
        self._show = checked
        self.repaintRequested.emit()
