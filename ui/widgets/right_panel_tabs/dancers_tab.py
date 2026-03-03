from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QWidget,
)

from ui.widgets.generic_widgets.collapsible_section import CollapsibleSection


@dataclass(frozen=True)
class DancerPersonalData:
    name: str
    height_cm: int


@dataclass(frozen=True)
class DancerLabelingData:
    label: str
    color: QColor


@dataclass(frozen=True)
class SkeletonPointData:
    name: str
    confidence: float


@dataclass(frozen=True)
class DancerSkeletonData:
    points: list[SkeletonPointData]


@dataclass(frozen=True)
class DancerProfileData:
    personal: DancerPersonalData
    labeling: DancerLabelingData
    skeleton: DancerSkeletonData


class SkeletonAPoseWidget(QWidget):
    _POINT_POSITIONS: dict[str, tuple[float, float]] = {
        "Nose": (0.5, 0.1),
        "Left Shoulder": (0.35, 0.27),
        "Right Shoulder": (0.65, 0.27),
        "Left Elbow": (0.22, 0.34),
        "Right Elbow": (0.78, 0.34),
        "Left Wrist": (0.1, 0.42),
        "Right Wrist": (0.9, 0.42),
        "Left Hip": (0.43, 0.52),
        "Right Hip": (0.57, 0.52),
        "Left Knee": (0.43, 0.72),
        "Right Knee": (0.57, 0.72),
        "Left Ankle": (0.43, 0.92),
        "Right Ankle": (0.57, 0.92),
    }

    _BONES: list[tuple[str, str]] = [
        ("Nose", "Left Shoulder"),
        ("Nose", "Right Shoulder"),
        ("Left Shoulder", "Left Elbow"),
        ("Left Elbow", "Left Wrist"),
        ("Right Shoulder", "Right Elbow"),
        ("Right Elbow", "Right Wrist"),
        ("Left Shoulder", "Left Hip"),
        ("Right Shoulder", "Right Hip"),
        ("Left Hip", "Right Hip"),
        ("Left Hip", "Left Knee"),
        ("Left Knee", "Left Ankle"),
        ("Right Hip", "Right Knee"),
        ("Right Knee", "Right Ankle"),
    ]

    def __init__(self, skeleton_data: DancerSkeletonData):
        super().__init__()
        self._skeleton_data = skeleton_data
        self.setMinimumHeight(300)

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        drawing_rect = QRectF(20, 10, self.width() - 200, self.height() - 20)
        legend_start_x = drawing_rect.right() + 16

        pen = QPen(QColor("#767676"))
        pen.setWidth(2)
        painter.setPen(pen)

        for start_name, end_name in self._BONES:
            start = self._scaled_point(start_name, drawing_rect)
            end = self._scaled_point(end_name, drawing_rect)
            painter.drawLine(start, end)

        point_data_map = {point.name: point for point in self._skeleton_data.points}
        for point_name, _ in self._POINT_POSITIONS.items():
            point = point_data_map.get(point_name)
            confidence = point.confidence if point else 0.2
            color = self._confidence_to_color(confidence)
            center = self._scaled_point(point_name, drawing_rect)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(center, 7, 7)

            painter.setPen(QColor("#D5D7DA"))
            y_offset = list(self._POINT_POSITIONS.keys()).index(point_name) * 20
            painter.drawText(
                QPointF(legend_start_x, 22 + y_offset),
                f"{point_name}: {int(round(confidence * 100))}%",
            )

    def _scaled_point(self, point_name: str, drawing_rect: QRectF) -> QPointF:
        x_factor, y_factor = self._POINT_POSITIONS[point_name]
        x = drawing_rect.left() + drawing_rect.width() * x_factor
        y = drawing_rect.top() + drawing_rect.height() * y_factor
        return QPointF(x, y)

    @staticmethod
    def _confidence_to_color(confidence: float) -> QColor:
        clamped = max(0.2, min(0.9, confidence))
        ratio = (clamped - 0.2) / 0.7
        red = int(round(255 * (1.0 - ratio)))
        green = int(round(255 * ratio))
        return QColor(red, green, 0)


class DancerProfileWidget(QWidget):
    def __init__(self, profile_data: DancerProfileData):
        super().__init__()
        self._profile_data = profile_data

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        personal_section = CollapsibleSection("Personal Data")
        personal_form: QFormLayout = personal_section.form_layout
        personal_form.addRow("Name", QLabel(profile_data.personal.name))
        personal_form.addRow("Height", QLabel(f"{profile_data.personal.height_cm} cm"))

        labeling_section = CollapsibleSection("Labeling")
        labeling_form: QFormLayout = labeling_section.form_layout
        labeling_form.addRow("Label", QLabel(profile_data.labeling.label))

        color_row = QWidget()
        color_layout = QHBoxLayout(color_row)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(6)

        self._color_preview = QFrame()
        self._color_preview.setFixedSize(18, 18)
        self._set_preview_color(profile_data.labeling.color)

        color_button = QPushButton("Pick color")
        color_button.clicked.connect(self._pick_color)

        color_layout.addWidget(self._color_preview)
        color_layout.addWidget(color_button)
        color_layout.addStretch(1)

        labeling_form.addRow("Color", color_row)

        skeleton_section = CollapsibleSection("MediaPipe Skeleton (A Pose)")
        skeleton_section.form_layout.addRow(SkeletonAPoseWidget(profile_data.skeleton))

        content_layout.addWidget(personal_section)
        content_layout.addWidget(labeling_section)
        content_layout.addWidget(skeleton_section)
        content_layout.addStretch(1)

        root_layout.addWidget(scroll)

    def _pick_color(self) -> None:
        selected = QColorDialog.getColor(
            self._profile_data.labeling.color,
            self,
            "Select label color",
        )
        if not selected.isValid():
            return
        self._profile_data = DancerProfileData(
            personal=self._profile_data.personal,
            labeling=DancerLabelingData(label=self._profile_data.labeling.label, color=selected),
            skeleton=self._profile_data.skeleton,
        )
        self._set_preview_color(selected)

    def _set_preview_color(self, color: QColor) -> None:
        self._color_preview.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #808080; border-radius: 3px;"
        )


class DancersTabWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.West)

        leader_profile = self._mock_profile(
            name="Alex",
            height_cm=177,
            label="Leader",
            color=QColor("#1E90FF"),
        )
        follower_profile = self._mock_profile(
            name="Mia",
            height_cm=165,
            label="Follower",
            color=QColor("#FF69B4"),
        )

        leader_widget = DancerProfileWidget(leader_profile)
        follower_widget = DancerProfileWidget(follower_profile)

        leader_idx = tabs.addTab(leader_widget, self._symbol_icon("♂"), "")
        follower_idx = tabs.addTab(follower_widget, self._symbol_icon("♀"), "")
        tabs.setTabToolTip(leader_idx, "Leader")
        tabs.setTabToolTip(follower_idx, "Follower")

        layout.addWidget(tabs)

    def _mock_profile(self, name: str, height_cm: int, label: str, color: QColor) -> DancerProfileData:
        points = [
            SkeletonPointData(name="Nose", confidence=0.87),
            SkeletonPointData(name="Left Shoulder", confidence=0.83),
            SkeletonPointData(name="Right Shoulder", confidence=0.88),
            SkeletonPointData(name="Left Elbow", confidence=0.75),
            SkeletonPointData(name="Right Elbow", confidence=0.79),
            SkeletonPointData(name="Left Wrist", confidence=0.62),
            SkeletonPointData(name="Right Wrist", confidence=0.67),
            SkeletonPointData(name="Left Hip", confidence=0.9),
            SkeletonPointData(name="Right Hip", confidence=0.89),
            SkeletonPointData(name="Left Knee", confidence=0.72),
            SkeletonPointData(name="Right Knee", confidence=0.74),
            SkeletonPointData(name="Left Ankle", confidence=0.61),
            SkeletonPointData(name="Right Ankle", confidence=0.64),
        ]
        return DancerProfileData(
            personal=DancerPersonalData(name=name, height_cm=height_cm),
            labeling=DancerLabelingData(label=label, color=color),
            skeleton=DancerSkeletonData(points=points),
        )

    @staticmethod
    def _symbol_icon(symbol: str) -> QIcon:
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        path.addText(3, 16, font, symbol)
        painter.fillPath(path, QColor("#D5D7DA"))
        painter.end()
        return QIcon(pixmap)
