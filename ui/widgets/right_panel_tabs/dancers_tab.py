from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class PersonalData:
    name: str
    height_cm: int


@dataclass(frozen=True)
class LabelingData:
    label: str
    color_hex: str


@dataclass(frozen=True)
class SkeletonData:
    point_scores: dict[str, float]


class PersonalDataMockSource:
    def __init__(self, name: str, height_cm: int):
        self._data = PersonalData(name=name, height_cm=height_cm)

    def read(self) -> PersonalData:
        return self._data


class LabelingDataMockSource:
    def __init__(self, label: str, color_hex: str):
        self._data = LabelingData(label=label, color_hex=color_hex)

    def read(self) -> LabelingData:
        return self._data


class SkeletonDataMockSource:
    def __init__(self, point_scores: dict[str, float]):
        self._data = SkeletonData(point_scores=point_scores)

    def read(self) -> SkeletonData:
        return self._data


class SkeletonViewWidget(QWidget):
    _POINT_COORDS: dict[str, tuple[float, float]] = {
        "Nose": (0.50, 0.12),
        "Left shoulder": (0.40, 0.28),
        "Right shoulder": (0.60, 0.28),
        "Left elbow": (0.30, 0.38),
        "Right elbow": (0.70, 0.38),
        "Left wrist": (0.20, 0.44),
        "Right wrist": (0.80, 0.44),
        "Left hip": (0.44, 0.50),
        "Right hip": (0.56, 0.50),
        "Left knee": (0.44, 0.68),
        "Right knee": (0.56, 0.68),
        "Left ankle": (0.44, 0.86),
        "Right ankle": (0.56, 0.86),
    }

    _CONNECTIONS: list[tuple[str, str]] = [
        ("Nose", "Left shoulder"),
        ("Nose", "Right shoulder"),
        ("Left shoulder", "Right shoulder"),
        ("Left shoulder", "Left elbow"),
        ("Left elbow", "Left wrist"),
        ("Right shoulder", "Right elbow"),
        ("Right elbow", "Right wrist"),
        ("Left shoulder", "Left hip"),
        ("Right shoulder", "Right hip"),
        ("Left hip", "Right hip"),
        ("Left hip", "Left knee"),
        ("Right hip", "Right knee"),
        ("Left knee", "Left ankle"),
        ("Right knee", "Right ankle"),
    ]

    def __init__(self, skeleton_data: SkeletonData):
        super().__init__()
        self._skeleton_data = skeleton_data
        self.setMinimumHeight(320)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        drawing_area = QRectF(16, 16, self.width() - 32, self.height() - 32)

        painter.setPen(QPen(QColor("#8A8A8A"), 2))
        for point_a, point_b in self._CONNECTIONS:
            painter.drawLine(self._map_to_area(drawing_area, point_a), self._map_to_area(drawing_area, point_b))

        for point_name, score in self._skeleton_data.point_scores.items():
            point = self._map_to_area(drawing_area, point_name)
            color = self._score_to_color(score)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(point, 7, 7)

            painter.setPen(QPen(QColor("#EAEAEA")))
            painter.drawText(QPointF(point.x() + 10, point.y() + 4), f"{int(score * 100)}%")

    def _map_to_area(self, rect: QRectF, point_name: str) -> QPointF:
        x_ratio, y_ratio = self._POINT_COORDS[point_name]
        return QPointF(rect.left() + rect.width() * x_ratio, rect.top() + rect.height() * y_ratio)

    @staticmethod
    def _score_to_color(score: float) -> QColor:
        min_score = 0.2
        max_score = 0.9
        clamped = max(min(score, max_score), min_score)
        ratio = (clamped - min_score) / (max_score - min_score)
        red = int(255 * (1 - ratio))
        green = int(255 * ratio)
        return QColor(red, green, 0)


class _DancerProfileWidget(QWidget):
    def __init__(
        self,
        personal_data_source: PersonalDataMockSource,
        labeling_data_source: LabelingDataMockSource,
        skeleton_data_source: SkeletonDataMockSource,
    ):
        super().__init__()

        personal_data = personal_data_source.read()
        labeling_data = labeling_data_source.read()
        skeleton_data = skeleton_data_source.read()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        personal_group = QGroupBox("Personal Data")
        personal_form = QFormLayout(personal_group)
        personal_form.addRow("Name", QLabel(personal_data.name))
        personal_form.addRow("Height", QLabel(f"{personal_data.height_cm} cm"))

        labeling_group = QGroupBox("Labeling")
        labeling_form = QFormLayout(labeling_group)
        labeling_form.addRow("Label", QLabel(labeling_data.label))

        color_chip = QFrame()
        color_chip.setFixedSize(20, 20)
        color_chip.setStyleSheet(
            f"background-color: {labeling_data.color_hex}; border: 1px solid #666666; border-radius: 4px;"
        )
        color_row = QWidget()
        color_layout = QHBoxLayout(color_row)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.addWidget(color_chip)
        color_layout.addWidget(QLabel(labeling_data.color_hex))
        color_layout.addStretch(1)
        labeling_form.addRow("Color", color_row)

        skeleton_group = QGroupBox("MediaPipe Skeleton (A pose)")
        skeleton_layout = QVBoxLayout(skeleton_group)
        skeleton_layout.addWidget(SkeletonViewWidget(skeleton_data))

        layout.addWidget(personal_group)
        layout.addWidget(labeling_group)
        layout.addWidget(skeleton_group)
        layout.addStretch(1)


class DancersTabWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        dancer_tabs = QTabWidget()
        dancer_tabs.setTabPosition(QTabWidget.TabPosition.West)

        leader_widget = _DancerProfileWidget(
            personal_data_source=PersonalDataMockSource("Alex", 178),
            labeling_data_source=LabelingDataMockSource("Lead A", "#4C78FF"),
            skeleton_data_source=SkeletonDataMockSource(
                {
                    "Nose": 0.88,
                    "Left shoulder": 0.82,
                    "Right shoulder": 0.84,
                    "Left elbow": 0.72,
                    "Right elbow": 0.78,
                    "Left wrist": 0.64,
                    "Right wrist": 0.68,
                    "Left hip": 0.81,
                    "Right hip": 0.79,
                    "Left knee": 0.73,
                    "Right knee": 0.75,
                    "Left ankle": 0.62,
                    "Right ankle": 0.67,
                }
            ),
        )

        follower_widget = _DancerProfileWidget(
            personal_data_source=PersonalDataMockSource("Taylor", 165),
            labeling_data_source=LabelingDataMockSource("Follow B", "#FF4CA8"),
            skeleton_data_source=SkeletonDataMockSource(
                {
                    "Nose": 0.86,
                    "Left shoulder": 0.77,
                    "Right shoulder": 0.79,
                    "Left elbow": 0.66,
                    "Right elbow": 0.70,
                    "Left wrist": 0.58,
                    "Right wrist": 0.63,
                    "Left hip": 0.80,
                    "Right hip": 0.78,
                    "Left knee": 0.71,
                    "Right knee": 0.72,
                    "Left ankle": 0.60,
                    "Right ankle": 0.61,
                }
            ),
        )

        leader_index = dancer_tabs.addTab(leader_widget, "♂")
        dancer_tabs.tabBar().setTabToolTip(leader_index, "Leader")

        follower_index = dancer_tabs.addTab(follower_widget, "♀")
        dancer_tabs.tabBar().setTabToolTip(follower_index, "Follower")

        layout.addWidget(dancer_tabs)
