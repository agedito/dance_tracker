from typing import Callable

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QScrollArea,
    QVBoxLayout, QWidget,
)

from app.interface.sequence_data import Bookmark
from ui.widgets.timeline import TimelineTrack
from ui.widgets.viewport_overview_bar import ViewportOverviewBar


class TimelinePanel(QFrame):
    """Single responsibility: display timeline tracks for all layers."""

    def __init__(
            self,
            total_frames: int,
            layers: list,
            on_frame_changed: Callable[[int], None],
            on_scrub_start: Callable,
            on_scrub_end: Callable,
            on_bookmark_requested: Callable[[int], None],
            on_bookmark_moved: Callable[[int, int], None],
            on_bookmark_removed: Callable[[int], None],
            on_bookmark_name_changed: Callable[[int, str], None],
            on_bookmark_lock_changed: Callable[[int, bool], None],
    ):
        super().__init__()
        self.setObjectName("Panel")

        self.time_info = QLabel("")
        self.time_info.setObjectName("Muted")
        self.zoom_bar = QProgressBar()
        self.zoom_bar.setRange(0, 100)
        self.zoom_bar.setValue(0)
        self.zoom_bar.setFixedWidth(140)
        self.zoom_bar.setTextVisible(True)
        self.zoom_bar.setFormat("Zoom 0% · Pan 0%")
        self.viewport_bar = ViewportOverviewBar()
        self.track_widgets: list[TimelineTrack] = []
        self._shared_view_start = 0.0
        self._shared_view_span = 1.0
        self._syncing_viewport = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("PanelHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.addWidget(QLabel("MASTER TIMELINE"))
        hl.addWidget(self.zoom_bar)
        hl.addWidget(self.viewport_bar)
        hl.addStretch(1)
        hl.addWidget(self.time_info)
        root.addWidget(header)

        # Scroll area with tracks
        scroll = QScrollArea()
        scroll.setObjectName("ScrollArea")
        scroll.setWidgetResizable(True)

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        for layer in layers:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(10)

            name = QLabel(layer.name)
            name.setObjectName("LayerName")
            name.setFixedWidth(160)

            track = TimelineTrack(total_frames, layer.segments)
            track.frameChanged.connect(on_frame_changed)
            track.scrubStarted.connect(on_scrub_start)
            track.scrubFinished.connect(on_scrub_end)
            track.bookmarkRequested.connect(on_bookmark_requested)
            track.bookmarkMoved.connect(on_bookmark_moved)
            track.bookmarkRemoved.connect(on_bookmark_removed)
            track.bookmarkNameChanged.connect(on_bookmark_name_changed)
            track.bookmarkLockChanged.connect(on_bookmark_lock_changed)
            self.track_widgets.append(track)
            track.viewportChanged.connect(self._sync_viewport_from_track)

            rl.addWidget(name)
            rl.addWidget(track, 1)
            lay.addWidget(row)

        lay.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)
        self._update_viewport_indicators(self._shared_view_start, self._shared_view_span)

    def set_frame(self, frame: int):
        for track in self.track_widgets:
            track.set_frame(frame)

    def set_total_frames(self, total: int):
        for track in self.track_widgets:
            track.set_total_frames(total)

    def set_bookmarks(self, bookmarks: list[Bookmark]):
        for track in self.track_widgets:
            track.set_bookmarks(bookmarks)

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

    def _sync_viewport_from_track(self, start: float, span: float):
        if self._syncing_viewport:
            return

        self._shared_view_start = start
        self._shared_view_span = span
        self._syncing_viewport = True
        try:
            for track in self.track_widgets:
                track.set_shared_viewport(self._shared_view_start, self._shared_view_span)
        finally:
            self._syncing_viewport = False

        self._update_viewport_indicators(self._shared_view_start, self._shared_view_span)

    def _update_viewport_indicators(self, start: float, span: float):
        self._update_zoom_bar(start, span)
        self.viewport_bar.set_viewport(start, span)

    def _update_zoom_bar(self, start: float, span: float):
        if not self.track_widgets:
            self.zoom_bar.setValue(0)
            self.zoom_bar.setFormat("Zoom 0% · Pan 0%")
            return
        normalized = (1.0 - span) / 0.99
        zoom_value = int(round(max(0.0, min(1.0, normalized)) * 100.0))
        pan_value = int(round(max(0.0, min(1.0, start)) * 100.0))
        self.zoom_bar.setValue(zoom_value)
        self.zoom_bar.setFormat(f"Zoom {zoom_value}% · Pan {pan_value}%")
