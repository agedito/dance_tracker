from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea,
    QSlider, QVBoxLayout, QWidget,
)

from app.interface.sequence_data import Bookmark
from ui.widgets.timeline import TimelineTrack


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
    ):
        super().__init__()
        self.setObjectName("Panel")

        self.time_info = QLabel("")
        self.time_info.setObjectName("Muted")
        self.track_widgets: list[TimelineTrack] = []
        self.total_frames = max(1, total_frames)
        self._zoom_factor = 1.0
        self._view_start_frame = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("PanelHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.addWidget(QLabel("MASTER TIMELINE"))
        self.zoom_label = QLabel("Zoom: 1.0x")
        self.zoom_label.setObjectName("Muted")
        self.zoom_slider = QSlider()
        self.zoom_slider.setOrientation(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 80)
        self.zoom_slider.setValue(10)
        self.zoom_slider.setFixedWidth(140)
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        hl.addWidget(self.zoom_label)
        hl.addWidget(self.zoom_slider)
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
            track.zoomRequested.connect(self._on_zoom_requested)
            self.track_widgets.append(track)

            rl.addWidget(name)
            rl.addWidget(track, 1)
            lay.addWidget(row)

        lay.addStretch(1)
        self.pan_slider = QSlider(Qt.Orientation.Horizontal)
        self.pan_slider.setRange(0, 0)
        self.pan_slider.valueChanged.connect(self._on_pan_slider_changed)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)
        root.addWidget(self.pan_slider)

        self._refresh_view()

    def set_frame(self, frame: int):
        for track in self.track_widgets:
            track.set_frame(frame)

    def set_total_frames(self, total: int):
        self.total_frames = max(1, total)
        for track in self.track_widgets:
            track.set_total_frames(total)
        self._refresh_view()

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

    def _visible_frame_count(self) -> int:
        return max(1, int(round(self.total_frames / self._zoom_factor)))

    def _max_view_start(self) -> int:
        return max(0, self.total_frames - self._visible_frame_count())

    def _refresh_view(self):
        self._view_start_frame = max(0, min(self._view_start_frame, self._max_view_start()))
        self.zoom_label.setText(f"Zoom: {self._zoom_factor:.1f}x")
        self.pan_slider.blockSignals(True)
        self.pan_slider.setRange(0, self._max_view_start())
        self.pan_slider.setValue(self._view_start_frame)
        self.pan_slider.setEnabled(self._max_view_start() > 0)
        self.pan_slider.blockSignals(False)
        for track in self.track_widgets:
            track.set_view(self._zoom_factor, self._view_start_frame)

    def _on_zoom_slider_changed(self, value: int):
        old_visible = self._visible_frame_count()
        old_center = self._view_start_frame + (old_visible // 2)
        self._zoom_factor = max(1.0, value / 10.0)
        new_visible = self._visible_frame_count()
        self._view_start_frame = old_center - (new_visible // 2)
        self._refresh_view()

    def _on_zoom_requested(self, step: float):
        next_zoom = max(1.0, min(8.0, self._zoom_factor * step))
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(int(round(next_zoom * 10)))
        self.zoom_slider.blockSignals(False)
        self._on_zoom_slider_changed(self.zoom_slider.value())

    def _on_pan_slider_changed(self, value: int):
        self._view_start_frame = value
        self._refresh_view()
