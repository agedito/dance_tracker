from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QLabel,
)

from app.interface.sequence_data import SequenceDataPort, SequenceVideoData


class CollapsibleSection(QWidget):
    def __init__(self, title: str):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._toggle = QToolButton(self)
        self._toggle.setText(title)
        self._toggle.setCheckable(True)
        self._toggle.setChecked(True)
        self._toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle.setArrowType(Qt.ArrowType.DownArrow)
        self._toggle.toggled.connect(self._on_toggled)

        self._content = QGroupBox(self)
        self._content_layout = QFormLayout(self._content)
        self._content_layout.setContentsMargins(8, 12, 8, 8)

        layout.addWidget(self._toggle)
        layout.addWidget(self._content)

    @property
    def form_layout(self) -> QFormLayout:
        return self._content_layout

    def _on_toggled(self, expanded: bool) -> None:
        self._toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self._content.setVisible(expanded)


class DataTabWidget(QWidget):
    def __init__(self, sequence_data: SequenceDataPort):
        super().__init__()
        self._sequence_data = sequence_data

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        video_section = CollapsibleSection("Video")
        video_layout = video_section.form_layout

        self._resolution_value = QLabel("—")
        self._length_value = QLabel("—")
        self._duration_value = QLabel("—")
        self._frames_value = QLabel("—")
        self._fps_value = QLabel("—")

        video_layout.addRow("Resolution", self._resolution_value)
        video_layout.addRow("Length", self._length_value)
        video_layout.addRow("Duration", self._duration_value)
        video_layout.addRow("Frames", self._frames_value)
        video_layout.addRow("FPS", self._fps_value)

        dance_section = CollapsibleSection("Dance")
        dance_layout = dance_section.form_layout

        self._dance_style_value = QLabel("—")
        self._song_value = QLabel("—")
        self._follower_value = QLabel("—")
        self._leader_value = QLabel("—")
        self._event_value = QLabel("—")
        self._year_value = QLabel("—")

        dance_layout.addRow("Dance style", self._dance_style_value)
        dance_layout.addRow("Song", self._song_value)
        dance_layout.addRow("Follower", self._follower_value)
        dance_layout.addRow("Leader", self._leader_value)
        dance_layout.addRow("Event", self._event_value)
        dance_layout.addRow("Year", self._year_value)

        layout.addWidget(video_section)
        layout.addWidget(dance_section)
        layout.addStretch(1)

    def update_from_sequence(self, frames_folder_path: str) -> None:
        data = self._sequence_data.read_video_data(frames_folder_path)
        if not data:
            self._reset()
            return

        self._apply_data(data)

    def clear(self) -> None:
        self._reset()

    def _apply_data(self, data: SequenceVideoData) -> None:
        self._resolution_value.setText(f"{data.resolution_width} x {data.resolution_height}")
        self._length_value.setText(self._format_length(data.length_bytes))
        self._duration_value.setText(self._format_duration(data.duration_seconds))
        self._frames_value.setText(str(data.frames))
        self._fps_value.setText(f"{data.fps:.3f}".rstrip("0").rstrip("."))
        self._dance_style_value.setText(data.dance_style)
        self._song_value.setText(data.song)
        self._follower_value.setText(data.follower)
        self._leader_value.setText(data.leader)
        self._event_value.setText(data.event)
        self._year_value.setText(data.year)

    def _reset(self) -> None:
        self._resolution_value.setText("—")
        self._length_value.setText("—")
        self._duration_value.setText("—")
        self._frames_value.setText("—")
        self._fps_value.setText("—")
        self._dance_style_value.setText("—")
        self._song_value.setText("—")
        self._follower_value.setText("—")
        self._leader_value.setText("—")
        self._event_value.setText("—")
        self._year_value.setText("—")

    @staticmethod
    def _format_length(length_bytes: int) -> str:
        if length_bytes <= 0:
            return "—"

        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(length_bytes)
        unit_idx = 0
        while value >= 1024 and unit_idx < len(units) - 1:
            value /= 1024
            unit_idx += 1
        return f"{value:.2f} {units[unit_idx]}"

    @staticmethod
    def _format_duration(seconds: float) -> str:
        if seconds <= 0:
            return "—"

        total_seconds = int(round(seconds))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
