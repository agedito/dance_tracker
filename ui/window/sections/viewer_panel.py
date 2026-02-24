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
            on_play: Callable,
            on_pause: Callable,
            on_step: Callable[[int], None],
            on_next_error: Callable,
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

        buttons = [
            ("PLAY", "PrimaryButton", on_play),
            ("PAUSE", None, on_pause),
            ("STEP BACK", None, lambda: on_step(-1)),
            ("STEP FORWARD", None, lambda: on_step(1)),
            ("NEXT ERROR", None, on_next_error),
        ]
        for label, obj_name, callback in buttons:
            btn = QPushButton(label)
            if obj_name:
                btn.setObjectName(obj_name)
            btn.clicked.connect(callback)
            fl.addWidget(btn)

        fl.addStretch(1)
        root.addWidget(footer)

    def update_frame_label(self, frame: int):
        self.frame_info.setText(f"Frame: {frame}")
