from typing import Callable

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.interface.application import DanceTrackerPort
from app.track_app.frame_state.frame_store import FrameStore
from ui.widgets.viewer import ViewerWidget


class ViewerPanel(QFrame):
    """Single responsibility: viewer display and transport controls."""

    cornerDragged = Signal(int, int)

    def __init__(
            self,
            app: DanceTrackerPort,
            total_frames: int,
            fps: int,
            frame_store: FrameStore,
            on_play_pause_toggle: Callable,
            on_step: Callable[[int], None],
            on_prev_bookmark: Callable,
            on_next_bookmark: Callable,
    ):
        super().__init__()
        self.setObjectName("Panel")
        self._fps = max(1, int(fps))

        self.frame_info = QLabel("Frame: 0 · Time: 00:00.000")
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
        self.play_pause_btn.setProperty("transportControl", True)
        self.play_pause_btn.clicked.connect(on_play_pause_toggle)
        self._set_play_icon()
        fl.addWidget(self.play_pause_btn)

        buttons = [
            ("↩🔖", "Go to previous bookmark", on_prev_bookmark),
            ("←", "Step back one frame", lambda: on_step(-1)),
            ("→", "Step forward one frame", lambda: on_step(1)),
            ("🔖↪", "Go to next bookmark", on_next_bookmark),
        ]
        for icon, tooltip, callback in buttons:
            btn = QPushButton(icon)
            btn.setToolTip(tooltip)
            btn.setProperty("transportControl", True)
            btn.clicked.connect(callback)
            fl.addWidget(btn)

        fl.addStretch(1)
        root.addWidget(footer)

        self._corner_handle = _PanelCornerHandle(self)
        self._corner_handle.dragged.connect(self.cornerDragged)
        self._position_corner_handle()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_corner_handle()

    def _position_corner_handle(self) -> None:
        handle_size = self._corner_handle.sizeHint()
        x = self.width() - handle_size.width()
        y = self.height() - handle_size.height()
        self._corner_handle.setGeometry(x, y, handle_size.width(), handle_size.height())
        self._corner_handle.raise_()

    def update_frame_label(self, frame: int):
        total_ms = int((max(0, frame) / self._fps) * 1000)
        minutes, rem_ms = divmod(total_ms, 60_000)
        seconds, milliseconds = divmod(rem_ms, 1000)
        self.frame_info.setText(
            f"Frame: {frame} · Time: {minutes:02d}:{seconds:02d}.{milliseconds:03d}"
        )

    def update_playback_button(self, is_playing: bool) -> None:
        if is_playing:
            self.play_pause_btn.setToolTip("Pause")
            self._set_pause_icon()
            return
        self.play_pause_btn.setToolTip("Play")
        self._set_play_icon()

    def _set_play_icon(self) -> None:
        self.play_pause_btn.setText("▶")
        self.play_pause_btn.setStyleSheet("color: #35C76F;")

    def _set_pause_icon(self) -> None:
        self.play_pause_btn.setText("⏸")
        self.play_pause_btn.setStyleSheet("color: #D84C4C;")


class _PanelCornerHandle(QFrame):
    """Draggable bottom-right corner handle for two-axis panel resizing."""

    dragged = Signal(int, int)

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._last_global_pos: QPoint | None = None
        self.setFixedSize(18, 18)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip("Drag to resize viewer area horizontally and vertically")
        self.setStyleSheet(
            "background-color: rgba(100, 100, 100, 120);"
            "border-top-left-radius: 6px;"
            "border: 1px solid rgba(210, 210, 210, 120);"
        )

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return

        self._last_global_pos = event.globalPosition().toPoint()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self._last_global_pos is None:
            event.ignore()
            return

        current_pos = event.globalPosition().toPoint()
        delta = current_pos - self._last_global_pos
        self._last_global_pos = current_pos
        self.dragged.emit(delta.x(), delta.y())
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._last_global_pos = None
            event.accept()
            return
        event.ignore()
