"""
MainWindow — thin orchestrator.

Each concern lives in its own class:
  - PreferencesManager → persistence of user prefs / layout / session
  - PlaybackController → play / pause / timer tick / error navigation
  - FolderSessionManager → folder loading, session restore, frame memory
  - TopBar → top bar widget with recent-folder icons
  - ViewerPanel → main video viewer and transport buttons
  - RightPanel → layer thumbnails + 3D pose viewer
  - TimelinePanel → master timeline with layer tracks
  - StatusPanel → status light, stats grid, beat markers
"""

from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow

from app.interface.application import DanceTrackerPort
from app.interface.music import SongMetadata
from app.track_app.frame_state.frame_store import FrameStore
from app.track_app.main_app import DanceTrackerApp
from ui.config import Config
from ui.window.layout import MainWindowLayout
from ui.window.sections.folder_session_manager import FolderSessionManager
from ui.window.sections.playback_controller import PlaybackController
from ui.window.sections.preferences_manager import PreferencesManager
from ui.window.sections.right_panel import RightPanel
from ui.window.sections.status_panel import StatusPanel
from ui.window.sections.timeline_panel import TimelinePanel
from ui.window.sections.topbar import TopBar
from ui.window.sections.viewer_panel import ViewerPanel


class MainWindow(QMainWindow):
    def __init__(self, cfg: Config, old_app: DanceTrackerApp, app: DanceTrackerPort):
        super().__init__()
        self.cfg = cfg
        self.state = old_app.states_manager
        self._app = app

        # ── Collaborators ────────────────────────────────────────────
        self._prefs = PreferencesManager(cfg.max_recent_folders)

        self._frame_store = FrameStore(cache_radius=self.state.config.frame_cache_radius)

        self._playback = PlaybackController(
            fps=self.state.fps,
            state=self.state,
            on_frame_changed=self.set_frame,
        )
        self._scrubbing = False
        self._pending_scrub_frame: int | None = None
        self._scrub_timer = QTimer(self)
        self._scrub_timer.setSingleShot(True)
        self._scrub_timer.setInterval(16)
        self._scrub_timer.timeout.connect(self._flush_scrub_frame)
        self._loaded_count = 0
        self._loaded_frames: set[int] = set()
        self._active_preload_generation = 0
        self._preload_done = False
        self._frame_store.frame_preloaded.connect(self._on_frame_preloaded)
        self._frame_store.preload_finished.connect(self._on_preload_finished)

        self._folder_session = FolderSessionManager(
            preferences=self._prefs,
            frame_store=self._frame_store,
            on_frames_loaded=self._on_frames_loaded,
            on_icons_changed=self._on_recent_sources_changed,
        )

        # ── Window setup ─────────────────────────────────────────────
        self.setWindowTitle(cfg.title)
        self.resize(1200, 780)

        self._layout = MainWindowLayout(self, cfg.get_css())
        self._build_ui()
        self._folder_session.restore_last_session() or self.set_frame(0)

    # ── UI construction ──────────────────────────────────────────────

    def on_frames_loaded(self, path: str) -> None:
        self._folder_session.load_folder(path)

    def on_song_identified(self, song: SongMetadata) -> None:
        self._right_panel.update_song_info(song)

    def _log_message(self, message: str) -> None:
        self._right_panel.logger_widget.log(message)

    def _on_recent_sources_changed(self):
        if hasattr(self, "_topbar"):
            self._topbar.refresh_icons()
        if hasattr(self, "_right_panel"):
            self._right_panel.refresh_sequences()

    def _build_ui(self):
        self.setCentralWidget(self._layout.root)

        self._topbar = TopBar(
            on_close=self._close,
        )
        self._layout.set_topbar(self._topbar)

        self._viewer_panel = ViewerPanel(
            app=self._app,
            total_frames=self.state.total_frames,
            frame_store=self._frame_store,
            on_play=self._playback.play,
            on_pause=self._playback.pause,
            on_step=self._playback.step,
            on_next_error=self._playback.next_error,
        )
        self._viewer_panel.viewer.folderLoaded.connect(self._on_folder_dropped)

        self._right_panel = RightPanel(
            preferences=self._prefs,
            media_manager=self._app.media,
            on_sequence_removed=self._on_sequence_removed,
        )

        self._timeline = TimelinePanel(
            total_frames=self.state.total_frames,
            layers=self.state.layers,
            on_frame_changed=self._on_timeline_frame_changed,
            on_scrub_start=self._on_scrub_start,
            on_scrub_end=self._on_scrub_end,
        )

        self._status = StatusPanel(
            on_prev_error=self._playback.prev_error,
            on_next_error=self._playback.next_error,
        )

        self._layout.set_top_content(self._viewer_panel, self._right_panel)
        self._layout.set_bottom_content(self._timeline, self._status)
        self._layout.finalize()

        self._restore_splitters()
        self._connect_splitter_persistence()
        self._setup_shortcuts()

    # ── Shortcuts ────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        bindings = [
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
        ]
        self._shortcuts = []
        for shortcut, cb in bindings:
            sc = QShortcut(shortcut, self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(cb)
            self._shortcuts.append(sc)

    # ── Splitter layout persistence ──────────────────────────────────

    def _restore_splitters(self):
        self.showFullScreen()
        for name in ("top_splitter", "bottom_splitter", "main_splitter"):
            splitter = getattr(self._layout, name)
            sizes = self._prefs.splitter_sizes(name)
            if sizes:
                splitter.setSizes(sizes)

    def _connect_splitter_persistence(self):
        for name in ("top_splitter", "bottom_splitter", "main_splitter"):
            getattr(self._layout, name).splitterMoved.connect(self._save_splitters)

    def _save_splitters(self, *_):
        self._prefs.save_fullscreen(self.isFullScreen())
        for name in ("top_splitter", "bottom_splitter", "main_splitter"):
            self._prefs.save_splitter_sizes(name, getattr(self._layout, name).sizes())
        self._prefs.save()

    # ── Frame update (the single "sync all widgets" point) ───────────

    def set_frame(self, frame: int):
        self.state.set_frame(frame)
        cur = self.state.cur_frame
        self._frame_store.request_preload_priority(cur)

        self._viewer_panel.viewer.set_frame(cur)
        self._viewer_panel.update_frame_label(cur)

        self._timeline.set_frame(cur)
        self._timeline.update_info(
            self.state.total_frames,
            len(self.state.error_frames),
            loaded_count=self._loaded_count,
            preload_done=self._preload_done,
        )

        self._right_panel.update_pose(cur)

        self._status.update_status(
            cur_frame=cur,
            total_frames=self.state.total_frames,
            error_count=len(self.state.error_frames),
            is_error=cur in self.state.error_frames,
            is_playing=self.state.playing,
        )

    def _set_frame_lightweight(self, frame: int):
        self.state.set_frame(frame)
        cur = self.state.cur_frame
        self._frame_store.request_preload_priority(cur)
        self._viewer_panel.viewer.set_frame(cur)
        self._viewer_panel.update_frame_label(cur)
        self._timeline.set_frame(cur)

    def _on_timeline_frame_changed(self, frame: int):
        if not self._scrubbing:
            self.set_frame(frame)
            return

        self._pending_scrub_frame = frame
        self._set_frame_lightweight(frame)
        if not self._scrub_timer.isActive():
            self._scrub_timer.start()

    def _flush_scrub_frame(self):
        if self._pending_scrub_frame is None:
            return
        self.set_frame(self._pending_scrub_frame)
        self._pending_scrub_frame = None

    def _on_scrub_start(self):
        self._scrubbing = True
        self._pending_scrub_frame = None
        self._viewer_panel.viewer.set_proxy_frames_enabled(True)

    def _on_scrub_end(self):
        self._scrubbing = False
        self._viewer_panel.viewer.set_proxy_frames_enabled(False)
        self._flush_scrub_frame()


    def _on_frame_preloaded(self, frame: int, loaded: bool, generation: int):
        if generation != self._active_preload_generation:
            return
        if frame < 0 or frame >= self.state.total_frames:
            return

        if loaded:
            self._loaded_frames.add(frame)
        else:
            self._loaded_frames.discard(frame)

        flags = self._frame_store.loaded_flags
        self._loaded_frames = {i for i, is_loaded in enumerate(flags) if is_loaded}
        self._loaded_count = min(self.state.total_frames, len(self._loaded_frames))
        self._timeline.set_frame_loaded(frame, loaded)
        self._timeline.update_info(
            self.state.total_frames,
            len(self.state.error_frames),
            loaded_count=self._loaded_count,
            preload_done=self._preload_done,
        )

    def _on_preload_finished(self, generation: int):
        if generation != self._active_preload_generation:
            return
        self._loaded_count = min(self.state.total_frames, len(self._loaded_frames))
        self._preload_done = True
        self._log_message("Frame cache completed.")
        self._timeline.update_info(
            self.state.total_frames,
            len(self.state.error_frames),
            loaded_count=self._loaded_count,
            preload_done=self._preload_done,
        )

    # ── Folder / session events ──────────────────────────────────────

    def _on_frames_loaded(self, total_frames: int, initial_frame: int = 0):
        self._playback.pause()
        self._viewer_panel.viewer.set_proxy_frames_enabled(False)
        self.state.set_total_frames(total_frames)
        self._viewer_panel.viewer.set_total_frames(total_frames)
        self._timeline.set_total_frames(total_frames)
        loaded_flags = self._frame_store.loaded_flags
        self._timeline.set_loaded_flags(loaded_flags)
        self._loaded_frames = {i for i, loaded in enumerate(loaded_flags) if loaded}
        self._loaded_count = min(total_frames, len(self._loaded_frames))
        self._active_preload_generation = self._frame_store.preload_generation
        self._preload_done = self._loaded_count >= total_frames
        self._topbar.set_active_folder(self._folder_session.current_folder_path)
        self._right_panel.refresh_sequences()
        self._right_panel.set_active_sequence(self._folder_session.current_folder_path)
        source_name = Path(self._folder_session.current_folder_path or "").name or "sequence"
        self._log_message(f"Loaded media: {source_name}.")
        self.set_frame(initial_frame)

    def _on_folder_dropped(self, folder_path: str, total_frames: int):
        self._folder_session.on_folder_dropped(folder_path, self.state.cur_frame)
        self._on_frames_loaded(
            total_frames,
            initial_frame=self._prefs.saved_frame_for_folder(
                str(Path(folder_path).expanduser())
            ),
        )

    def _open_recent_folder(self, folder_path: str):
        normalized = str(Path(folder_path).expanduser())
        if normalized == self._folder_session.current_folder_path:
            return
        self._folder_session.load_folder(folder_path)

    def _on_sequence_removed(self, folder_path: str):
        normalized = str(Path(folder_path).expanduser())
        if normalized != self._folder_session.current_folder_path:
            return

        self._playback.pause()
        self._viewer_panel.viewer.set_proxy_frames_enabled(False)
        self._folder_session.current_folder_path = None
        self._frame_store.clear()
        self.state.set_total_frames(1000)
        self._viewer_panel.viewer.set_total_frames(self.state.total_frames)
        self._timeline.set_total_frames(self.state.total_frames)
        self._timeline.set_loaded_flags(self._frame_store.loaded_flags)
        self._loaded_frames = set()
        self._loaded_count = 0
        self._preload_done = False
        self._topbar.set_active_folder(None)
        self._right_panel.set_active_sequence(None)
        self.set_frame(0)

    # ── Lifecycle ────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent):
        self._folder_session.remember_current_frame(self.state.cur_frame)
        self._save_splitters()
        self._frame_store.shutdown()
        super().closeEvent(event)

    def _close(self):
        # to allow using that method as on_close param without warnings
        self.close()
