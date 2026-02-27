from typing import Callable

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel,
    QVBoxLayout, QWidget,
)

from ui.widgets.timeline import TimelineTrack


class TimelinePanel(QFrame):
    """Single responsibility: display the master timeline track."""

    def __init__(
            self,
            total_frames: int,
            layers: list,
            on_frame_changed: Callable[[int], None],
            on_scrub_start: Callable,
            on_scrub_end: Callable,
    ):
        super().__init__()
        self.setObjectName("Panel")

        self.time_info = QLabel("")
        self.time_info.setObjectName("Muted")
        self.track_widgets: list[TimelineTrack] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("PanelHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.addWidget(QLabel("Main timeline"))
        hl.addStretch(1)
        hl.addWidget(self.time_info)
        root.addWidget(header)

        # Single master timeline
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        track = TimelineTrack(total_frames, layers[0].segments if layers else [])
        track.frameChanged.connect(on_frame_changed)
        track.scrubStarted.connect(on_scrub_start)
        track.scrubFinished.connect(on_scrub_end)
        self.track_widgets.append(track)

        lay.addWidget(track)
        lay.addStretch(1)
        root.addWidget(content, 1, 0)

    def set_frame(self, frame: int):
        for track in self.track_widgets:
            track.set_frame(frame)

    def set_total_frames(self, total: int):
        for track in self.track_widgets:
            track.set_total_frames(total)

    def set_loaded_flags(self, flags: list[bool]):
        for track in self.track_widgets:
            track.set_loaded_flags(flags)

    def set_frame_loaded(self, frame: int, loaded: bool):
        for track in self.track_widgets:
            track.set_frame_loaded(frame, loaded)

    def update_info(
            self,
            total_frames: int,
            error_count: int,
            loaded_count: int | None = None,
            preload_done: bool = False,
    ):
        loaded_text = ""
        if loaded_count is not None:
            safe_total = max(1, total_frames)
            safe_loaded = max(0, min(loaded_count, safe_total))
            if preload_done or safe_loaded >= safe_total:
                loaded_text = f" · Loaded: {safe_loaded}/{safe_total}"
            else:
                pct = (safe_loaded / safe_total) * 100.0
                loaded_text = f" · Loaded: {safe_loaded}/{safe_total} ({pct:.2f}%)"

        self.time_info.setText(
            f"Total frames: {total_frames} · Error frames: {error_count}{loaded_text}"
        )
