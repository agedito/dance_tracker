from typing import Callable

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.interface.application import DanceTrackerPort
from app.track_app.frame_state.frame_store import FrameStore
from ui.widgets.viewer import ViewerWidget


class ViewerPanel(QFrame):
    """Single responsibility: viewer display and transport controls."""

    def __init__(
            self,
            app: DanceTrackerPort,
            total_frames: int,
            frame_store: FrameStore,
            on_play_pause_toggle: Callable,
            on_step: Callable[[int], None],
            on_prev_bookmark: Callable,
            on_next_bookmark: Callable,
    ):
        super().__init__()
        self.setObjectName("Panel")

        self.frame_info = QLabel("Frame: 0")
        self.frame_info.setObjectName("Muted")

        self.viewer = ViewerWidget(app, total_frames, frame_store=frame_store)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("PanelHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.addWidget(QLabel("Viewer"))
        hl.addStretch(1)
        hl.addWidget(self.frame_info)
        root.addWidget(header)

        # Viewer
        root.addWidget(self.viewer, 1)

        # Footer (transport controls)
        footer = QWidget()
        footer.setObjectName("PanelFooter")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(10, 10, 10, 10)
        fl.setSpacing(8)

        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setObjectName("PrimaryButton")
        self.play_pause_btn.setToolTip("Play")
        self.play_pause_btn.clicked.connect(on_play_pause_toggle)
        fl.addWidget(self.play_pause_btn)

        buttons = [
            ("⏮", "Go to previous bookmark", on_prev_bookmark),
            ("⏪", "Step back one frame", lambda: on_step(-1)),
            ("⏩", "Step forward one frame", lambda: on_step(1)),
            ("⏭", "Go to next bookmark", on_next_bookmark),
        ]
        for icon, tooltip, callback in buttons:
            btn = QPushButton(icon)
            btn.setToolTip(tooltip)
            btn.clicked.connect(callback)
            fl.addWidget(btn)

        fl.addStretch(1)
        root.addWidget(footer)

    def update_frame_label(self, frame: int):
        self.frame_info.setText(f"Frame: {frame}")

    def update_playback_button(self, is_playing: bool) -> None:
        if is_playing:
            self.play_pause_btn.setText("⏸")
            self.play_pause_btn.setToolTip("Pause")
            return
        self.play_pause_btn.setText("▶")
        self.play_pause_btn.setToolTip("Play")
