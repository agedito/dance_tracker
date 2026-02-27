from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from app.interface.sequence_data import SequenceDataPort, SequenceVideoData


class DataTabWidget(QWidget):
    def __init__(self, sequence_data: SequenceDataPort):
        super().__init__()
        self._sequence_data = sequence_data

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        video_group = QGroupBox("Video")
        video_layout = QFormLayout(video_group)
        video_layout.setContentsMargins(8, 12, 8, 8)

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

        layout.addWidget(video_group)
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

    def _reset(self) -> None:
        self._resolution_value.setText("—")
        self._length_value.setText("—")
        self._duration_value.setText("—")
        self._frames_value.setText("—")
        self._fps_value.setText("—")

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
