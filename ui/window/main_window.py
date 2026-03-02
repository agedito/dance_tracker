"""
MainWindow — thin orchestrator.

Each concern lives in its own class:
  - PreferencesManager    → persistence of user prefs / layout / session
  - PlaybackController    → play / pause / timer tick / error navigation
  - FolderSessionManager  → folder loading, session restore, frame memory
  - ScrubberController    → scrub throttling and proxy enable/disable
  - PreloadTracker        → per-frame preload progress from FrameStore signals
  - LayoutPersistence     → splitter sizes and screen assignment save/restore
  - BookmarkController    → bookmark CRUD dispatch to App port
  - TopBar                → top bar widget with recent-folder icons
  - ViewerPanel           → main video viewer and transport buttons
  - RightPanel            → layer thumbnails + 3D pose viewer
  - TimelinePanel         → master timeline with layer tracks
  - StatusPanel           → status light, stats grid, beat markers
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow

from app.interface.application import DanceTrackerPort
from app.interface.event_bus import EventBus
from app.interface.music import SongMetadata
from app.interface.sequences import SequenceState
from ui.config import Config
from ui.widgets.frame_store import FrameStore
from ui.window.layout import MainWindowLayout
from ui.window.sections.bookmark_controller import BookmarkController
from ui.window.sections.folder_session_manager import FolderSessionManager
from ui.window.sections.layout_persistence import LayoutPersistence
from ui.window.sections.playback_controller import PlaybackController
from ui.window.sections.preferences_manager import PreferencesManager
from ui.window.sections.preload_tracker import PreloadTracker
from ui.window.sections.right_panel import RightPanel
from ui.window.sections.scrubber_controller import ScrubberController
from ui.window.sections.status_panel import StatusPanel
from ui.window.sections.timeline_panel import TimelinePanel
from ui.window.sections.topbar import TopBar
from ui.window.sections.viewer_panel import ViewerPanel


class MainWindow(QMainWindow):
    def __init__(self, cfg: Config, app: DanceTrackerPort, events: EventBus, prefs: PreferencesManager):
        super().__init__()
        self.cfg = cfg
        self._app = app
        self._frames = app.frames
        self._events = events

        self._prefs = prefs
        self._frame_store = FrameStore(cache_radius=self._frames.frame_cache_radius)
        self._playback = PlaybackController(
            fps=self._frames.fps,
            frames=self._frames,
            on_frame_changed=self.set_frame,
        )
        self._preload_tracker = PreloadTracker(
            frame_store=self._frame_store,
            on_frame_loaded=self._on_preload_frame_loaded,
            on_finished=self._on_preload_complete,
        )
        self._frame_store.frame_preloaded.connect(self._preload_tracker.on_frame_preloaded)
        self._frame_store.preload_finished.connect(self._preload_tracker.on_preload_finished)

        self._folder_session = FolderSessionManager(
            preferences=self._prefs,
            frame_store=self._frame_store,
            on_frames_loaded=self._on_frames_loaded,
        )

        self.setWindowTitle(cfg.title)
        self.resize(1200, 780)

        self._layout = MainWindowLayout(self, cfg.get_css())
        self._build_ui()

        self._layout_persistence = LayoutPersistence(self._layout, self._prefs, self)
        self._layout_persistence.restore()
        self._layout_persistence.connect_save_on_move()

        self.set_frame(0)

    # ── EventBus handlers ────────────────────────────────────────────

    def on_frames_loaded(self, path: str) -> None:
        self._right_panel.set_current_folder_path(path)
        self._right_panel.update_sequence_data(path)
        self._app.track_detector.load_detections(path)
        self._folder_session.load_folder(path)

    def on_song_identified(self, song: SongMetadata) -> None:
        self._right_panel.update_song_info(song)

    def on_sequences_changed(self, state: SequenceState) -> None:
        self._topbar.set_active_folder(state.active_folder)
        current = self._folder_session.current_folder_path
        if current and not any(item.folder_path == current for item in state.items):
            self._clear_loaded_sequence()

    def on_detections_updated(self, frames_folder_path: str) -> None:
        self._viewer_panel.viewer.update()
        source_name = Path(frames_folder_path).name or "sequence"
        self._log_message(f"Detections updated for: {source_name}.")

    def on_bookmarks_changed(self, frames_folder_path: str) -> None:
        current = self._folder_session.current_folder_path
        if current and Path(current).expanduser() == Path(frames_folder_path).expanduser():
            self._bookmarks.refresh()

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self):
        self.setCentralWidget(self._layout.root)

        self._topbar = TopBar(
            on_close=self._close,
            sequence_data=self._app.sequence_data,
        )
        self._layout.set_topbar(self._topbar)

        self._bookmarks = BookmarkController(
            sequence_data=self._app.sequence_data,
            folder_session=self._folder_session,
            get_total_frames=lambda: self._frames.total_frames,
            get_cur_frame=lambda: self._frames.cur_frame,
            on_bookmarks_refreshed=lambda bm: self._timeline.set_bookmarks(bm),
            on_go_to_frame=self.set_frame,
        )

        self._viewer_panel = ViewerPanel(
            app=self._app,
            total_frames=self._frames.total_frames,
            fps=self._frames.fps,
            frame_store=self._frame_store,
            on_play_pause_toggle=self._toggle_playback,
            on_step=self._playback.step,
            on_prev_bookmark=self._bookmarks.go_to_previous,
            on_next_bookmark=self._bookmarks.go_to_next,
        )
        self._viewer_panel.viewer.folderLoaded.connect(self._on_folder_dropped)

        self._scrubber = ScrubberController(
            set_proxy_enabled=self._viewer_panel.viewer.set_proxy_frames_enabled,
            on_frame=self.set_frame,
            on_frame_lightweight=self._set_frame_lightweight,
        )

        self._right_panel = RightPanel(
            preferences=self._prefs,
            app=self._app,
            event_bus=self._events,
        )

        self._timeline = TimelinePanel(
            total_frames=self._frames.total_frames,
            layers=self._frames.layers,
            on_frame_changed=self._scrubber.on_timeline_frame_changed,
            on_scrub_start=self._scrubber.on_start,
            on_scrub_end=self._scrubber.on_end,
            on_bookmark_requested=self._bookmarks.request_add,
            on_bookmark_moved=self._bookmarks.request_move,
            on_bookmark_removed=self._bookmarks.request_remove,
            on_bookmark_name_changed=self._bookmarks.request_name_change,
            on_bookmark_lock_changed=self._bookmarks.request_lock_change,
        )

        self._status = StatusPanel(
            on_prev_error=self._playback.prev_error,
            on_next_error=self._playback.next_error,
        )

        self._layout.set_top_content(self._viewer_panel, self._right_panel)
        self._layout.set_bottom_content(self._timeline, self._status)
        self._layout.finalize()

        self._setup_shortcuts()

    def _setup_shortcuts(self):
        bindings = [
            (QKeySequence(Qt.Key.Key_Space), self._toggle_playback),
            (QKeySequence(Qt.Key.Key_Left), lambda: self._playback.step(-1)),
            (QKeySequence(Qt.Key.Key_Right), lambda: self._playback.step(1)),
            (QKeySequence(Qt.Key.Key_A), lambda: self._playback.step(-1)),
            (QKeySequence(Qt.Key.Key_D), lambda: self._playback.step(1)),
            (QKeySequence(Qt.Key.Key_PageUp), lambda: self._playback.step(-10)),
            (QKeySequence(Qt.Key.Key_PageDown), lambda: self._playback.step(10)),
            (QKeySequence(Qt.Key.Key_Home), self._playback.go_to_start),
            (QKeySequence(Qt.Key.Key_End), self._playback.go_to_end),
            (QKeySequence("Ctrl+A"), self._playback.go_to_start),
            (QKeySequence("Ctrl+D"), self._playback.go_to_end),
            (QKeySequence("Ctrl+Left"), self._playback.go_to_start),
            (QKeySequence("Ctrl+Right"), self._playback.go_to_end),
            (QKeySequence("Shift+A"), self._bookmarks.go_to_previous),
            (QKeySequence("Shift+D"), self._bookmarks.go_to_next),
            (QKeySequence("Shift+Left"), self._bookmarks.go_to_previous),
            (QKeySequence("Shift+Right"), self._bookmarks.go_to_next),
            (QKeySequence(Qt.Key.Key_Q), self._close),
        ]
        self._shortcuts = []
        for shortcut, cb in bindings:
            sc = QShortcut(shortcut, self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(cb)
            self._shortcuts.append(sc)

    def _toggle_playback(self):
        if self._frames.playing:
            self._playback.pause()
        else:
            self._playback.play()

    # ── Frame sync ───────────────────────────────────────────────────

    def set_frame(self, frame: int):
        cur = self._frames.set_frame(frame)
        self._frame_store.request_preload_priority(cur)

        self._viewer_panel.viewer.set_frame(cur)
        self._viewer_panel.update_frame_label(cur)
        self._viewer_panel.update_playback_button(self._frames.playing)

        self._timeline.set_frame(cur)
        self._timeline.update_info(
            self._frames.total_frames,
            len(self._frames.error_frames),
            loaded_count=self._preload_tracker.loaded_count,
            preload_done=self._preload_tracker.preload_done,
        )

        self._right_panel.update_pose(cur)

        self._status.update_status(
            cur_frame=cur,
            total_frames=self._frames.total_frames,
            error_count=len(self._frames.error_frames),
            is_error=cur in self._frames.error_frames,
            is_playing=self._frames.playing,
        )

    def _set_frame_lightweight(self, frame: int):
        cur = self._frames.set_frame(frame)
        self._frame_store.request_preload_priority(cur)
        self._viewer_panel.viewer.set_frame(cur)
        self._viewer_panel.update_frame_label(cur)
        self._viewer_panel.update_playback_button(self._frames.playing)
        self._timeline.set_frame(cur)

    # ── Preload callbacks ─────────────────────────────────────────────

    def _on_preload_frame_loaded(self, frame: int, loaded: bool, loaded_count: int, preload_done: bool) -> None:
        self._timeline.set_frame_loaded(frame, loaded)
        self._timeline.update_info(
            self._frames.total_frames,
            len(self._frames.error_frames),
            loaded_count=loaded_count,
            preload_done=preload_done,
        )

    def _on_preload_complete(self, loaded_count: int, preload_done: bool) -> None:
        self._log_message("Frame cache completed.")
        self._timeline.update_info(
            self._frames.total_frames,
            len(self._frames.error_frames),
            loaded_count=loaded_count,
            preload_done=preload_done,
        )

    # ── Folder / session events ──────────────────────────────────────

    def _on_frames_loaded(self, total_frames: int, initial_frame: int = 0):
        self._playback.pause()
        self._viewer_panel.viewer.set_proxy_frames_enabled(False)
        self._frames.set_total_frames(total_frames)
        self._viewer_panel.viewer.set_total_frames(total_frames)
        self._timeline.set_total_frames(total_frames)
        loaded_flags = self._frame_store.loaded_flags
        self._timeline.set_loaded_flags(loaded_flags)
        self._preload_tracker.reset(total_frames, self._frame_store.preload_generation, loaded_flags)
        self._bookmarks.refresh()
        source_name = Path(self._folder_session.current_folder_path or "").name or "sequence"
        self._log_message(f"Loaded media: {source_name}.")
        self.set_frame(initial_frame)

    def _on_folder_dropped(self, folder_path: str, total_frames: int):
        self._folder_session.on_folder_dropped(folder_path, self._frames.cur_frame)
        self._on_frames_loaded(
            total_frames,
            initial_frame=self._prefs.saved_frame_for_folder(
                str(Path(folder_path).expanduser())
            ),
        )

    def _clear_loaded_sequence(self):
        self._playback.pause()
        self._viewer_panel.viewer.set_proxy_frames_enabled(False)
        self._folder_session.current_folder_path = None
        self._frame_store.clear()
        self._frames.set_total_frames(1000)
        self._viewer_panel.viewer.set_total_frames(self._frames.total_frames)
        self._timeline.set_total_frames(self._frames.total_frames)
        self._timeline.set_loaded_flags(self._frame_store.loaded_flags)
        self._preload_tracker.reset(1000, self._frame_store.preload_generation, self._frame_store.loaded_flags)
        self._topbar.set_active_folder(None)
        self._right_panel.set_current_folder_path(None)
        self._right_panel.clear_sequence_data()
        self._bookmarks.refresh()
        self.set_frame(0)

    # ── Lifecycle ────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent):
        self._folder_session.remember_current_frame(self._frames.cur_frame)
        self._layout_persistence.save_screen()
        self._layout_persistence.save()
        self._frame_store.shutdown()
        super().closeEvent(event)

    def _close(self):
        self.close()

    def _log_message(self, message: str) -> None:
        self._right_panel.logger_widget.log(message)
