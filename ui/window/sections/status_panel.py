from typing import Callable

from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)

from ui.widgets.beat_marker import BeatMarkerWidget
from ui.widgets.status_light import StatusLight


class StatusPanel(QFrame):
    """Single responsibility: display status info, frame navigator, and beat markers."""

    def __init__(self, on_prev_error: Callable, on_next_error: Callable):
        super().__init__()
        self.setObjectName("Panel")

        v = QVBoxLayout(self)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(12)

        # Status header
        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)

        hl.addWidget(self._section_label("STATUS BAR"))
        self.status_light = StatusLight("gray", diameter=18)
        self.status_text = QLabel("gray")
        self.status_text.setObjectName("Muted")
        hl.addWidget(self.status_light)
        hl.addWidget(self.status_text)
        hl.addStretch(1)
        v.addWidget(header)

        # Stats grid
        self.stat_total = self._bold_value("-")
        self.stat_err = self._bold_value("-")
        self.stat_cur = self._bold_value("-")

        grid = QGridLayout()
        grid.setSpacing(6)
        grid.addWidget(self._muted_label("Total frames"), 0, 0)
        grid.addWidget(self.stat_total, 0, 1)
        grid.addWidget(self._muted_label("Error frames"), 1, 0)
        grid.addWidget(self.stat_err, 1, 1)
        grid.addWidget(self._muted_label("Current frame"), 2, 0)
        grid.addWidget(self.stat_cur, 2, 1)
        v.addLayout(grid)

        # Navigation
        v.addWidget(self._section_label("FRAME NAVIGATOR"))
        nav = QWidget()
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(0, 0, 0, 0)
        nl.setSpacing(8)
        prev_btn = QPushButton("PREVIOUS ERROR")
        next_btn = QPushButton("NEXT ERROR")
        prev_btn.clicked.connect(on_prev_error)
        next_btn.clicked.connect(on_next_error)
        nl.addWidget(prev_btn)
        nl.addWidget(next_btn)
        v.addWidget(nav)

        v.addWidget(self._muted_label("FRAME"))
        self.frame_big = QLabel("0")
        self.frame_big.setObjectName("FrameBig")
        v.addWidget(self.frame_big)

        # Beat markers
        v.addWidget(self._section_label("MUSICAL BEATS (1-8)"))
        self.beat_marker = BeatMarkerWidget(beats=8)
        self.beat_info = QLabel("Pulso activo: ninguno")
        self.beat_info.setObjectName("Muted")
        self.beat_marker.beatChanged.connect(self._on_beat_changed)
        v.addWidget(self.beat_marker)
        v.addWidget(self.beat_info)

        v.addStretch(1)

    def update(self, cur_frame: int, total_frames: int, error_count: int,
               is_error: bool, is_playing: bool):
        self.stat_total.setText(str(total_frames))
        self.stat_err.setText(str(error_count))
        self.stat_cur.setText(str(cur_frame))
        self.frame_big.setText(str(cur_frame))

        if total_frames <= 1:
            status = "gray"
        elif is_error:
            status = "red"
        elif is_playing:
            status = "yellow"
        else:
            status = "green"

        self.status_light.set_status(status)
        self.status_text.setText(status)

    def _on_beat_changed(self, beat: int | None):
        if beat is None:
            self.beat_info.setText("Pulso activo: ninguno")
        else:
            self.beat_info.setText(f"Pulso activo: {beat}")

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionTitle")
        return label

    @staticmethod
    def _muted_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("Muted")
        return label

    @staticmethod
    def _bold_value(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("BoldValue")
        return label
