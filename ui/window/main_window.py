"""Main window orchestrator for widgets and app events."""

from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QMainWindow

from app.interface.application import AppState, DanceTrackerPort
from app.interface.music import SongMetadata
from app.track_app.frame_state.frame_store import FrameStore
from ui.config import Config
from ui.window.layout import MainWindowLayout
from ui.window.sections.folder_session_manager import FolderSessionManager
from ui.window.sections.preferences_manager import PreferencesManager
from ui.window.sections.right_panel import RightPanel
from ui.window.sections.status_panel import StatusPanel
from ui.window.sections.timeline_panel import TimelinePanel
from ui.window.sections.topbar import TopBar
from ui.window.sections.viewer_panel import ViewerPanel


class MainWindow(QMainWindow):
    def __init__(self, cfg: Config, app: DanceTrackerPort):
        super().__init__()
        self.cfg = cfg
        self._app = app
        self._app_state = app.get_state()

        self._prefs = PreferencesManager(cfg.max_recent_folders)
        self._frame_store = FrameStore(cache_radius=max(1, self._app_state.frame_cache_radius))

        self._scrubbing = False
        self._pending_scrub_frame: int | None = None
        self._scrub_timer = QTimer(self)
        self._scrub_timer.setSingleShot(True)
        self._scrub_timer.setInterval(16)
        self._scrub_timer.timeout.connect(self._flush_scrub_frame)

        self._play_timer = QTimer(self)
        self._play_timer.setInterval(int(1000 / max(1, self._app_state.fps)))
        self._play_timer.timeout.connect(self._app.advance_playback)

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

        self.setWindowTitle(cfg.title)
        self.resize(1200, 780)

        self._layout = MainWindowLayout(self, cfg.get_css())
        self._build_ui()
        self._folder_session.restore_last_session() or self._app.set_frame(0)

    def on_frames_loaded(self, path: str) -> None:
        self._folder_session.load_folder(path)
        self._app.set_current_folder(self._folder_session.current_folder_path)

    def on_song_identified(self, song: SongMetadata) -> None:
        self._right_panel.update_song_info(song)

    def on_app_state_changed(self, state: AppState) -> None:
        self._apply_app_state(state)

    def on_log_message(self, message: str) -> None:
        self._log_message(message)

    def _log_message(self, message: str) -> None:
        self._right_panel.logger_widget.log(message)

    def _on_recent_sources_changed(self):
        if hasattr(self, "_topbar"):
            self._topbar.refresh_icons()
        if hasattr(self, "_right_panel"):
            self._right_panel.refresh_sequences()

    def _build_ui(self):
        self.setCentralWidget(self._layout.root)

        self._topbar = TopBar(on_close=self._close)
        self._layout.set_topbar(self._topbar)

        self._viewer_panel = ViewerPanel(
            app=self._app,
            total_frames=self._app_state.total_frames,
            frame_store=self._frame_store,
            on_play=self._app.play,
            on_pause=self._app.pause,
            on_step=self._app.step,
            on_next_error=self._app.next_error,
        )
        self._viewer_panel.viewer.folderLoaded.connect(self._on_folder_dropped)

        self._right_panel = RightPanel(
            preferences=self._prefs,
            media_manager=self._app.media,
            on_sequence_removed=self._on_sequence_removed,
        )

        self._timeline = TimelinePanel(
            total_frames=self._app_state.total_frames,
            layers=list(self._app_state.layers),
            on_frame_changed=self._on_timeline_frame_changed,
            on_scrub_start=self._on_scrub_start,
            on_scrub_end=self._on_scrub_end,
        )

        self._status = StatusPanel(on_prev_error=self._app.prev_error, on_next_error=self._app.next_error)

        self._layout.set_top_content(self._viewer_panel, self._right_panel)
        self._layout.set_bottom_content(self._timeline, self._status)
        self._layout.finalize()

        self._restore_splitters()
        self._connect_splitter_persistence()
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        bindings = [
            (QKeySequence(Qt.Key.Key_Space), self._app.toggle_playback),
            (QKeySequence(Qt.Key.Key_Left), lambda: self._app.step(-1)),
            (QKeySequence(Qt.Key.Key_Right), lambda: self._app.step(1)),
            (QKeySequence(Qt.Key.Key_A), lambda: self._app.step(-1)),
            (QKeySequence(Qt.Key.Key_D), lambda: self._app.step(1)),
            (QKeySequence(Qt.Key.Key_PageUp), lambda: self._app.step(-10)),
            (QKeySequence(Qt.Key.Key_PageDown), lambda: self._app.step(10)),
            (QKeySequence(Qt.Key.Key_Home), self._app.go_to_start),
            (QKeySequence(Qt.Key.Key_End), self._app.go_to_end),
            (QKeySequence("Ctrl+A"), self._app.go_to_start),
            (QKeySequence("Ctrl+D"), self._app.go_to_end),
        ]
        self._shortcuts = []
        for shortcut, cb in bindings:
            sc = QShortcut(shortcut, self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(cb)
            self._shortcuts.append(sc)

    def _restore_splitters(self):
        self._restore_window_screen()
        self.showFullScreen()
        for name in ("top_splitter", "bottom_splitter", "main_splitter"):
            splitter = getattr(self._layout, name)
            sizes = self._prefs.splitter_sizes(name)
            if sizes:
                splitter.setSizes(sizes)

    def _restore_window_screen(self):
        screen_name = self._prefs.last_screen_name()
        if not screen_name:
            return
        for screen in QApplication.screens():
            if screen.name() == screen_name:
                self.setGeometry(screen.availableGeometry())
                return

    def _connect_splitter_persistence(self):
        for name in ("top_splitter", "bottom_splitter", "main_splitter"):
            getattr(self._layout, name).splitterMoved.connect(self._save_splitters)

    def _save_splitters(self, *_):
        self._prefs.save_fullscreen(self.isFullScreen())
        for name in ("top_splitter", "bottom_splitter", "main_splitter"):
            self._prefs.save_splitter_sizes(name, getattr(self._layout, name).sizes())
        self._prefs.save()

    def _apply_app_state(self, state: AppState):
        self._app_state = state
        self._play_timer.setInterval(int(1000 / max(1, state.fps)))
        if state.playing:
            if not self._play_timer.isActive():
                self._play_timer.start()
        else:
            self._play_timer.stop()

        cur = state.cur_frame
        self._frame_store.request_preload_priority(cur)
        self._viewer_panel.viewer.set_total_frames(state.total_frames)
        self._viewer_panel.viewer.set_frame(cur)
        self._viewer_panel.update_frame_label(cur)
        self._timeline.set_total_frames(state.total_frames)
        self._timeline.set_frame(cur)
        self._timeline.update_info(
            state.total_frames,
            len(state.error_frames),
            loaded_count=self._loaded_count,
            preload_done=self._preload_done,
        )
        self._right_panel.update_pose(cur)
        self._status.update_status(
            cur_frame=cur,
            total_frames=state.total_frames,
            error_count=len(state.error_frames),
            is_error=cur in set(state.error_frames),
            is_playing=state.playing,
        )
        self._topbar.set_active_folder(state.current_folder)
        self._right_panel.set_active_sequence(state.current_folder)

    def _set_frame_lightweight(self, frame: int):
        self._viewer_panel.viewer.set_frame(frame)
        self._viewer_panel.update_frame_label(frame)
        self._timeline.set_frame(frame)

    def _on_timeline_frame_changed(self, frame: int):
        if not self._scrubbing:
            self._app.set_frame(frame)
            return
        self._pending_scrub_frame = frame
        self._set_frame_lightweight(frame)
        if not self._scrub_timer.isActive():
            self._scrub_timer.start()

    def _flush_scrub_frame(self):
        if self._pending_scrub_frame is None:
            return
        self._app.set_frame(self._pending_scrub_frame)
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
        if frame < 0 or frame >= self._app_state.total_frames:
            return
        if loaded:
            self._loaded_frames.add(frame)
        else:
            self._loaded_frames.discard(frame)
        flags = self._frame_store.loaded_flags
        self._loaded_frames = {i for i, is_loaded in enumerate(flags) if is_loaded}
        self._loaded_count = min(self._app_state.total_frames, len(self._loaded_frames))
        self._timeline.set_frame_loaded(frame, loaded)
        self._timeline.update_info(
            self._app_state.total_frames,
            len(self._app_state.error_frames),
            loaded_count=self._loaded_count,
            preload_done=self._preload_done,
        )

    def _on_preload_finished(self, generation: int):
        if generation != self._active_preload_generation:
            return
        self._loaded_count = min(self._app_state.total_frames, len(self._loaded_frames))
        self._preload_done = True
        self._log_message("Frame cache completed.")
        self._timeline.update_info(
            self._app_state.total_frames,
            len(self._app_state.error_frames),
            loaded_count=self._loaded_count,
            preload_done=self._preload_done,
        )

    def _on_frames_loaded(self, total_frames: int, initial_frame: int = 0):
        self._app.pause()
        self._viewer_panel.viewer.set_proxy_frames_enabled(False)
        self._app.set_total_frames(total_frames)
        loaded_flags = self._frame_store.loaded_flags
        self._timeline.set_loaded_flags(loaded_flags)
        self._loaded_frames = {i for i, loaded in enumerate(loaded_flags) if loaded}
        self._loaded_count = min(total_frames, len(self._loaded_frames))
        self._active_preload_generation = self._frame_store.preload_generation
        self._preload_done = self._loaded_count >= total_frames
        source_name = Path(self._folder_session.current_folder_path or "").name or "sequence"
        self._log_message(f"Loaded media: {source_name}.")
        self._app.set_frame(initial_frame)

    def _on_folder_dropped(self, folder_path: str, total_frames: int):
        self._folder_session.on_folder_dropped(folder_path, self._app_state.cur_frame)
        self._app.set_current_folder(self._folder_session.current_folder_path)
        self._on_frames_loaded(
            total_frames,
            initial_frame=self._prefs.saved_frame_for_folder(str(Path(folder_path).expanduser())),
        )

    def _on_sequence_removed(self, folder_path: str):
        normalized = str(Path(folder_path).expanduser())
        if normalized != self._folder_session.current_folder_path:
            return
        self._app.pause()
        self._viewer_panel.viewer.set_proxy_frames_enabled(False)
        self._folder_session.current_folder_path = None
        self._app.set_current_folder(None)
        self._frame_store.clear()
        self._app.set_total_frames(1000)
        self._timeline.set_loaded_flags(self._frame_store.loaded_flags)
        self._loaded_frames = set()
        self._loaded_count = 0
        self._preload_done = False
        self._app.set_frame(0)

    def closeEvent(self, event: QCloseEvent):
        self._folder_session.remember_current_frame(self._app_state.cur_frame)
        current_screen = self.windowHandle().screen() if self.windowHandle() else None
        self._prefs.save_last_screen_name(current_screen.name() if current_screen else None)
        self._save_splitters()
        self._frame_store.shutdown()
        super().closeEvent(event)

    def _close(self):
        self.close()
