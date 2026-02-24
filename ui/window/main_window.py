import math
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton, QMenu, QScrollArea, QVBoxLayout, QWidget

from app.frame_state.frame_store import FrameStore
from app.main_app import DanceTrackerApp
from ui.config import Config
from ui.widgets.beat_marker import BeatMarkerWidget
from ui.widgets.pose_3d_viewer import Pose3DViewerWidget
from ui.widgets.status_light import StatusLight
from ui.widgets.thumbnail import ThumbnailWidget
from ui.widgets.timeline import TimelineTrack
from ui.widgets.viewer import ViewerWidget
from ui.window.layout import MainWindowLayout
from ui.window.preferences import load_preferences, save_preferences


class MainWindow(QMainWindow):
    def __init__(self, cfg: Config, app: DanceTrackerApp):
        super().__init__()
        self.cfg = cfg
        self.state = app.states_manager

        self.timer = QTimer(self)
        self.timer.setInterval(int(1000 / self.state.fps))
        self.timer.timeout.connect(self._tick)

        self.setWindowTitle(cfg.title)
        self.resize(1200, 780)
        self._preferences = load_preferences()
        self._current_folder_path: str | None = None

        self.layout = MainWindowLayout(self, cfg.get_css())

        self._create_widgets()
        self._restore_last_session()

    def _create_widgets(self):
        self.setCentralWidget(self.layout.root)

        self.layout.set_topbar(self._topbar())

        self.viewer_block = self._viewer_block()
        self.right_panel = self._right_panel()

        self.timeline_panel = self._timeline_panel()
        self.status_panel = self._status_panel()

        self.layout.set_top_content(self.viewer_block, self.right_panel)
        self.layout.set_bottom_content(self.timeline_panel, self.status_panel)
        self.layout.finalize()

        self.top_splitter = self.layout.top_splitter
        self.bottom_splitter = self.layout.bottom_splitter
        self.main_splitter = self.layout.main_splitter

        self._load_layout_preferences()
        self._connect_layout_persistence()
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        shortcuts = [
            (QKeySequence(Qt.Key_Left), lambda: self.set_frame(self.state.cur_frame - 1)),
            (QKeySequence(Qt.Key_Right), lambda: self.set_frame(self.state.cur_frame + 1)),
            (QKeySequence(Qt.Key_Home), lambda: self.set_frame(0)),
            (
                QKeySequence(Qt.Key_End),
                lambda: self.set_frame(max(0, self.state.total_frames - 1)),
            ),
        ]

        self._shortcuts = []
        for key_sequence, callback in shortcuts:
            shortcut = QShortcut(key_sequence, self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    def _connect_layout_persistence(self):
        self.top_splitter.splitterMoved.connect(self._save_layout_preferences)
        self.bottom_splitter.splitterMoved.connect(self._save_layout_preferences)
        self.main_splitter.splitterMoved.connect(self._save_layout_preferences)

    def _load_layout_preferences(self):
        # La app siempre debe arrancar en pantalla completa.
        self.showFullScreen()

        top_sizes = self._preferences.get("top_splitter_sizes")
        if isinstance(top_sizes, list) and len(top_sizes) == 2:
            self.top_splitter.setSizes(top_sizes)

        bottom_sizes = self._preferences.get("bottom_splitter_sizes")
        if isinstance(bottom_sizes, list) and len(bottom_sizes) == 2:
            self.bottom_splitter.setSizes(bottom_sizes)

        main_sizes = self._preferences.get("main_splitter_sizes")
        if isinstance(main_sizes, list) and len(main_sizes) == 2:
            self.main_splitter.setSizes(main_sizes)

    def _save_layout_preferences(self, *_):
        self._preferences["fullscreen"] = self.isFullScreen()
        self._preferences["top_splitter_sizes"] = self.top_splitter.sizes()
        self._preferences["bottom_splitter_sizes"] = self.bottom_splitter.sizes()
        self._preferences["main_splitter_sizes"] = self.main_splitter.sizes()
        save_preferences(self._preferences)

    def closeEvent(self, event: QCloseEvent):
        self._remember_current_frame()
        self._save_layout_preferences()
        super().closeEvent(event)

    def _topbar(self):
        w = QWidget()
        w.setObjectName("TopBar")
        l = QHBoxLayout(w)
        l.setContentsMargins(12, 10, 12, 10)
        title = QLabel("MAIN VIEWER")
        title.setObjectName("TopTitle")
        hint = QLabel("Arrastra una carpeta o video al viewer para cargar frames")
        hint.setObjectName("TopHint")
        l.addWidget(title)
        self.recent_folders_bar = QWidget()
        self.recent_folders_layout = QHBoxLayout(self.recent_folders_bar)
        self.recent_folders_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_folders_layout.setSpacing(6)
        l.addSpacing(12)
        l.addWidget(self.recent_folders_bar)
        l.addStretch(1)
        l.addWidget(hint)
        close_button = QPushButton("✕")
        close_button.setObjectName("TopCloseButton")
        close_button.setToolTip("Cerrar aplicación")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self.close)
        l.addSpacing(10)
        l.addWidget(close_button)
        self._render_recent_folder_icons()
        return w

    def _recent_folders(self) -> list[str]:
        saved = self._preferences.get("recent_folders", [])
        if not isinstance(saved, list):
            return []
        folders = [item for item in saved if isinstance(item, str) and item]
        return folders[: self.cfg.max_recent_folders] or []

    def _register_recent_folder(self, folder_path: str):
        normalized = str(Path(folder_path).expanduser())
        folders = [path for path in self._recent_folders() if path != normalized]
        folders.insert(0, normalized)
        self._preferences["recent_folders"] = folders[: self.cfg.max_recent_folders]
        self._preferences["last_opened_folder"] = normalized
        save_preferences(self._preferences)
        self._render_recent_folder_icons()

    def _saved_frame_for_folder(self, folder_path: str) -> int:
        frames = self._preferences.get("last_frame_by_folder", {})
        if not isinstance(frames, dict):
            return 0
        frame = frames.get(folder_path, 0)
        return frame if isinstance(frame, int) else 0

    def _remember_current_frame(self):
        if not self._current_folder_path:
            return
        frames = self._preferences.get("last_frame_by_folder", {})
        if not isinstance(frames, dict):
            frames = {}
        frames[self._current_folder_path] = self.state.cur_frame
        self._preferences["last_frame_by_folder"] = frames
        self._preferences["last_opened_folder"] = self._current_folder_path
        save_preferences(self._preferences)

    def _load_recent_folder(self, folder_path: str, target_frame: int | None = None):
        self._remember_current_frame()
        frame_count = self.frame_store.load_folder(folder_path)
        if frame_count <= 0:
            return
        normalized = str(Path(folder_path).expanduser())
        self._current_folder_path = normalized
        self._register_recent_folder(folder_path)
        frame_to_restore = self._saved_frame_for_folder(normalized) if target_frame is None else target_frame
        self.on_frames_loaded(frame_count, initial_frame=frame_to_restore)

    def _restore_last_session(self):
        last_folder = self._preferences.get("last_opened_folder")
        if not isinstance(last_folder, str) or not last_folder:
            recent = self._recent_folders()
            last_folder = recent[0] if recent else None
        if last_folder:
            target_frame = self._saved_frame_for_folder(last_folder)
            self._load_recent_folder(last_folder, target_frame=target_frame)
            return
        self.set_frame(0)

    def _remove_recent_folder(self, folder_path: str):
        folders = [path for path in self._recent_folders() if path != folder_path]
        self._preferences["recent_folders"] = folders[: self.cfg.max_recent_folders]
        save_preferences(self._preferences)
        self._render_recent_folder_icons()

    def _render_recent_folder_icons(self):
        if not hasattr(self, "recent_folders_layout"):
            return

        while self.recent_folders_layout.count():
            item = self.recent_folders_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for folder in self._recent_folders():
            folder_name = Path(folder).name or Path(folder).anchor or folder
            button = QPushButton(folder_name)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setObjectName("RecentFolderIcon")
            button.setToolTip(folder)
            button.clicked.connect(lambda _checked=False, path=folder: self._load_recent_folder(path))

            button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            button.customContextMenuRequested.connect(
                lambda pos, path=folder, current_button=button: self._show_recent_folder_menu(
                    path,
                    current_button.mapToGlobal(pos),
                )
            )

            self.recent_folders_layout.addWidget(button)

    def _show_recent_folder_menu(self, folder_path: str, global_pos):
        menu = QMenu(self)
        remove_action = QAction("Eliminar carpeta", self)
        remove_action.triggered.connect(
            lambda _checked=False, path=folder_path: self._remove_recent_folder(path)
        )
        menu.addAction(remove_action)
        menu.exec(global_pos)

    @staticmethod
    def create_horizontal_layout(label: str, h_widgets: QWidget):
        block = QFrame()
        block.setObjectName("Panel")
        v = QVBoxLayout(block)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        header = QWidget()
        header.setObjectName("PanelHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.addWidget(QLabel(label))
        hl.addStretch(1)
        hl.addWidget(h_widgets)
        v.addWidget(header)

        return block, v

    def _viewer_block(self):
        self.viewer_info = QLabel("Frame: 0")
        self.viewer_info.setObjectName("Muted")
        self.frame_store = FrameStore(cache_radius=self.state.config.frame_cache_radius)
        self.viewer = ViewerWidget(self.state.total_frames, frame_store=self.frame_store)
        self.viewer.folderLoaded.connect(self._on_folder_loaded)
        block, v = self.create_horizontal_layout("Viewer", self.viewer_info)

        v.addWidget(self.viewer, 1)

        footer = QWidget()
        footer.setObjectName("PanelFooter")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(10, 10, 10, 10)
        fl.setSpacing(8)

        btn_play = QPushButton("PLAY")
        btn_play.setObjectName("PrimaryButton")
        btn_pause = QPushButton("PAUSE")
        btn_back = QPushButton("STEP BACK")
        btn_fwd = QPushButton("STEP FORWARD")
        btn_next = QPushButton("NEXT ERROR")

        btn_play.clicked.connect(self.play)
        btn_pause.clicked.connect(self.pause)
        btn_back.clicked.connect(lambda: self.set_frame(self.state.cur_frame - 1))
        btn_fwd.clicked.connect(lambda: self.set_frame(self.state.cur_frame + 1))
        btn_next.clicked.connect(self.next_error)

        fl.addWidget(btn_play)
        fl.addWidget(btn_pause)
        fl.addWidget(btn_back)
        fl.addWidget(btn_fwd)
        fl.addWidget(btn_next)
        fl.addStretch(1)

        v.addWidget(footer)
        return block

    def _right_panel(self):
        panel = QFrame()
        panel.setObjectName("Panel")
        v = QVBoxLayout(panel)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(10)

        label = QLabel("LAYER VIEWERS")
        label.setObjectName("SectionTitle")
        v.addWidget(label)
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.addWidget(self._thumb("Layer 1: Color Grade", 10), 0, 0)
        grid.addWidget(self._thumb("Layer 1: Output", 17), 0, 1)
        v.addLayout(grid)

        label = QLabel("LAYER 2: OBJECT MASK")
        label.setObjectName("SectionTitle")
        v.addWidget(label)
        grid2 = QGridLayout()
        grid2.setSpacing(8)
        grid2.addWidget(self._thumb("Layer 2: Mask", 24), 0, 0)
        grid2.addWidget(self._thumb("Layer 2: Overlay", 31), 0, 1)
        v.addLayout(grid2)

        label = QLabel("POSES 3D")
        label.setObjectName("SectionTitle")
        v.addWidget(label)
        self.pose_3d_viewer = Pose3DViewerWidget()
        v.addWidget(self.pose_3d_viewer, 1)

        v.addStretch(1)
        label = QLabel("Mock: thumbnails procedural + poses YOLO 3D.")
        label.setObjectName("FooterNote")
        v.addWidget(label)
        return panel

    @staticmethod
    def _mock_yolo_pose_detections(frame: int) -> list[dict]:
        t = frame * 0.08

        def person(cx: float, arm_offset: float, confidence: float = 0.95):
            kp = [
                [cx, 0.25, confidence],
                [cx - 0.03, 0.24, confidence],
                [cx + 0.03, 0.24, confidence],
                [cx - 0.06, 0.27, confidence],
                [cx + 0.06, 0.27, confidence],
                [cx - 0.10, 0.36, confidence],
                [cx + 0.10, 0.36, confidence],
                [cx - 0.16 - arm_offset, 0.46, confidence],
                [cx + 0.16 + arm_offset, 0.46, confidence],
                [cx - 0.20 - arm_offset, 0.56, confidence],
                [cx + 0.20 + arm_offset, 0.56, confidence],
                [cx - 0.08, 0.60, confidence],
                [cx + 0.08, 0.60, confidence],
                [cx - 0.09, 0.77, confidence],
                [cx + 0.09, 0.77, confidence],
                [cx - 0.09, 0.95, confidence],
                [cx + 0.09, 0.95, confidence],
            ]
            return {"keypoints": kp}

        characters = frame % 3
        if characters == 0:
            return []
        if characters == 1:
            return [person(0.5, 0.04 * math.sin(t))]
        return [
            person(0.36, 0.04 * math.sin(t)),
            person(0.64, 0.04 * math.cos(t + 0.5)),
        ]

    def _on_folder_loaded(self, folder_path: str, total_frames: int):
        self._remember_current_frame()
        self._current_folder_path = str(Path(folder_path).expanduser())
        self._register_recent_folder(folder_path)
        self.on_frames_loaded(total_frames, initial_frame=self._saved_frame_for_folder(self._current_folder_path))

    @staticmethod
    def _thumb(label: str, seed: int):
        f = QFrame()
        f.setObjectName("ThumbFrame")
        l = QVBoxLayout(f)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(ThumbnailWidget(label, seed))
        return f

    def _timeline_panel(self):
        self.time_info = QLabel("")
        self.time_info.setObjectName("Muted")
        panel, v = self.create_horizontal_layout("MASTER TIMELINE", self.time_info)

        scroll = QScrollArea()
        scroll.setObjectName("ScrollArea")
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.track_widgets = []

        lay = QVBoxLayout(content)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        for layer in self.state.layers:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(10)
            name = QLabel(layer.name)
            name.setObjectName("LayerName")
            name.setFixedWidth(160)
            track = TimelineTrack(self.state.total_frames, layer.segments)
            track.frameChanged.connect(self.set_frame)
            track.scrubStarted.connect(lambda: self.viewer.set_proxy_frames_enabled(True))
            track.scrubFinished.connect(lambda: self.viewer.set_proxy_frames_enabled(False))
            self.track_widgets.append(track)
            rl.addWidget(name)
            rl.addWidget(track, 1)
            lay.addWidget(row)

        lay.addStretch(1)
        scroll.setWidget(content)
        v.addWidget(scroll, 1)
        return panel

    def _status_panel(self):
        panel = QFrame()
        panel.setObjectName("Panel")
        v = QVBoxLayout(panel)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(12)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        label = QLabel("STATUS BAR")
        label.setObjectName("SectionTitle")
        self.status_light = StatusLight("gray", diameter=18)
        self.status_text = QLabel("gray")
        self.status_text.setObjectName("Muted")
        header_layout.addWidget(label)
        header_layout.addWidget(self.status_light)
        header_layout.addWidget(self.status_text)
        header_layout.addStretch(1)
        v.addWidget(header)
        self.stat_total = QLabel("-")
        self.stat_total.setObjectName("BoldValue")
        self.stat_err = QLabel("-")
        self.stat_err.setObjectName("BoldValue")
        self.stat_cur = QLabel("-")
        self.stat_cur.setObjectName("BoldValue")

        grid = QGridLayout()
        grid.setSpacing(6)
        a = QLabel("Total frames")
        a.setObjectName("Muted")
        b = QLabel("Error frames")
        b.setObjectName("Muted")
        c = QLabel("Current frame")
        c.setObjectName("Muted")
        grid.addWidget(a, 0, 0)
        grid.addWidget(self.stat_total, 0, 1)
        grid.addWidget(b, 1, 0)
        grid.addWidget(self.stat_err, 1, 1)
        grid.addWidget(c, 2, 0)
        grid.addWidget(self.stat_cur, 2, 1)
        v.addLayout(grid)

        nav = QWidget()
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(0, 0, 0, 0)
        nl.setSpacing(8)
        prev_btn = QPushButton("PREVIOUS ERROR")
        next_btn = QPushButton("NEXT ERROR")
        prev_btn.clicked.connect(self.prev_error)
        next_btn.clicked.connect(self.next_error)
        nl.addWidget(prev_btn)
        nl.addWidget(next_btn)
        label = QLabel("FRAME NAVIGATOR")
        label.setObjectName("SectionTitle")
        v.addWidget(label)
        v.addWidget(nav)
        label = QLabel("FRAME")
        label.setObjectName("Muted")
        v.addWidget(label)
        self.frame_big = QLabel("0")
        self.frame_big.setObjectName("FrameBig")
        v.addWidget(self.frame_big)

        beat_label = QLabel("MUSICAL BEATS (1-8)")
        beat_label.setObjectName("SectionTitle")
        v.addWidget(beat_label)

        self.beat_marker = BeatMarkerWidget(beats=8)
        self.beat_info = QLabel("Pulso activo: ninguno")
        self.beat_info.setObjectName("Muted")
        self.beat_marker.beatChanged.connect(self._on_beat_changed)
        v.addWidget(self.beat_marker)
        v.addWidget(self.beat_info)

        v.addStretch(1)
        return panel

    def _on_beat_changed(self, beat: int | None):
        if beat is None:
            self.beat_info.setText("Pulso activo: ninguno")
            return
        self.beat_info.setText(f"Pulso activo: {beat}")

    def on_frames_loaded(self, total_frames: int, initial_frame: int = 0):
        self.pause()
        self.viewer.set_proxy_frames_enabled(False)
        self.state.set_total_frames(total_frames)
        self.viewer.set_total_frames(total_frames)
        for tr in self.track_widgets:
            tr.set_total_frames(total_frames)
        self.set_frame(initial_frame)

    def set_frame(self, frame: int):
        self.state.set_frame(frame)
        self.viewer.set_frame(self.state.cur_frame)
        for tr in self.track_widgets:
            tr.set_frame(self.state.cur_frame)
        self.viewer_info.setText(f"Frame: {self.state.cur_frame}")
        self.time_info.setText(
            f"Total frames: {self.state.total_frames} · Error frames: {len(self.state.error_frames)}"
        )
        self.stat_total.setText(str(self.state.total_frames))
        self.stat_err.setText(str(len(self.state.error_frames)))
        self.stat_cur.setText(str(self.state.cur_frame))
        self.frame_big.setText(str(self.state.cur_frame))
        if hasattr(self, "pose_3d_viewer"):
            self.pose_3d_viewer.set_detections(self._mock_yolo_pose_detections(self.state.cur_frame))

        if self.state.total_frames <= 1:
            status = "gray"
        elif self.state.cur_frame in self.state.error_frames:
            status = "red"
        elif self.state.playing:
            status = "yellow"
        else:
            status = "green"

        self.status_light.set_status(status)
        self.status_text.setText(status)

    def play(self):
        if self.state.playing:
            return
        self.state.playing = True
        self.set_frame(self.state.cur_frame)
        self.timer.start()

    def pause(self):
        self.state.playing = False
        self.timer.stop()
        self.set_frame(self.state.cur_frame)

    def _tick(self):
        advanced = self.state.advance_if_playing()
        if not advanced and not self.state.playing:
            self.timer.stop()
            return
        self.set_frame(self.state.cur_frame)

    def next_error(self):
        updated = self.state.next_error_frame()
        if updated is not None:
            self.set_frame(updated)

    def prev_error(self):
        updated = self.state.prev_error_frame()
        if updated is not None:
            self.set_frame(updated)
