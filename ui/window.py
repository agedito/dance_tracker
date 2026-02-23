from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from pathlib import Path

from app.frame_store import FrameStore
from app.logic import ReviewState
from ui.widgets.thumbnail import ThumbnailWidget
from ui.widgets.timeline import TimelineTrack
from ui.widgets.viewer import ViewerWidget
from ui.preferences import load_preferences, save_preferences


class MainWindow(QMainWindow):
    MAX_RECENT_FOLDERS = 5

    def __init__(self, title: str, state: ReviewState):
        super().__init__()
        self.state = state

        self.timer = QTimer(self)
        self.timer.setInterval(int(1000 / self.state.fps))
        self.timer.timeout.connect(self._tick)

        self.setWindowTitle(title)
        self.resize(1200, 780)
        self._preferences = load_preferences()

        root = QWidget()
        self.setCentralWidget(root)
        root.setStyleSheet(self._qss())

        outer = QVBoxLayout(root)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(10)

        outer.addWidget(self._topbar())

        self.viewer_block = self._viewer_block()
        self.right_panel = self._right_panel()

        self.timeline_panel = self._timeline_panel()
        self.status_panel = self._status_panel()

        self.top_splitter = QSplitter(Qt.Horizontal)
        self.top_splitter.setChildrenCollapsible(False)
        self.top_splitter.addWidget(self.viewer_block)
        self.top_splitter.addWidget(self.right_panel)
        self.top_splitter.setStretchFactor(0, 3)
        self.top_splitter.setStretchFactor(1, 2)
        self.top_splitter.setSizes([720, 480])

        self.bottom_splitter = QSplitter(Qt.Horizontal)
        self.bottom_splitter.setChildrenCollapsible(False)
        self.bottom_splitter.addWidget(self.timeline_panel)
        self.bottom_splitter.addWidget(self.status_panel)
        self.bottom_splitter.setStretchFactor(0, 4)
        self.bottom_splitter.setStretchFactor(1, 2)
        self.bottom_splitter.setSizes([800, 400])

        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.addWidget(self.top_splitter)
        self.main_splitter.addWidget(self.bottom_splitter)
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 2)
        self.main_splitter.setSizes([470, 300])
        outer.addWidget(self.main_splitter, 1)

        self._load_layout_preferences()
        self._connect_layout_persistence()

        self.set_frame(0)

    def _connect_layout_persistence(self):
        self.top_splitter.splitterMoved.connect(self._save_layout_preferences)
        self.bottom_splitter.splitterMoved.connect(self._save_layout_preferences)
        self.main_splitter.splitterMoved.connect(self._save_layout_preferences)

    def _load_layout_preferences(self):
        if self._preferences.get("fullscreen", True):
            self.showMaximized()

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
        self._preferences["fullscreen"] = self.isMaximized() or self.isFullScreen()
        self._preferences["top_splitter_sizes"] = self.top_splitter.sizes()
        self._preferences["bottom_splitter_sizes"] = self.bottom_splitter.sizes()
        self._preferences["main_splitter_sizes"] = self.main_splitter.sizes()
        save_preferences(self._preferences)

    def closeEvent(self, event: QCloseEvent):
        self._save_layout_preferences()
        super().closeEvent(event)

    def _topbar(self):
        w = QWidget()
        w.setObjectName("TopBar")
        l = QHBoxLayout(w)
        l.setContentsMargins(12, 10, 12, 10)
        title = QLabel("MAIN VIEWER")
        title.setObjectName("TopTitle")
        hint = QLabel("Arrastra una carpeta al viewer para cargar frames")
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
        self._render_recent_folder_icons()
        return w

    def _recent_folders(self) -> list[str]:
        saved = self._preferences.get("recent_folders", [])
        if not isinstance(saved, list):
            return []
        folders = [item for item in saved if isinstance(item, str) and item]
        return folders[: self.MAX_RECENT_FOLDERS]

    def _register_recent_folder(self, folder_path: str):
        normalized = str(Path(folder_path).expanduser())
        folders = [path for path in self._recent_folders() if path != normalized]
        folders.insert(0, normalized)
        self._preferences["recent_folders"] = folders[: self.MAX_RECENT_FOLDERS]
        save_preferences(self._preferences)
        self._render_recent_folder_icons()

    def _load_recent_folder(self, folder_path: str):
        frame_count = self.frame_store.load_folder(folder_path)
        if frame_count <= 0:
            return
        self._register_recent_folder(folder_path)
        self.on_frames_loaded(frame_count)

    def _render_recent_folder_icons(self):
        if not hasattr(self, "recent_folders_layout"):
            return

        while self.recent_folders_layout.count():
            item = self.recent_folders_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for folder in self._recent_folders():
            button = QPushButton("📁")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setObjectName("RecentFolderIcon")
            button.setToolTip(folder)
            button.clicked.connect(lambda _checked=False, path=folder: self._load_recent_folder(path))
            self.recent_folders_layout.addWidget(button)

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

        v.addStretch(1)
        label = QLabel("Mock: thumbnails procedural.")
        label.setObjectName("FooterNote")
        v.addWidget(label)
        return panel

    def _on_folder_loaded(self, folder_path: str, total_frames: int):
        self._register_recent_folder(folder_path)
        self.on_frames_loaded(total_frames)

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

        label = QLabel("STATUS BAR")
        label.setObjectName("SectionTitle")
        v.addWidget(label)
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

        v.addStretch(1)
        return panel

    def on_frames_loaded(self, total_frames: int):
        self.pause()
        self.state.set_total_frames(total_frames)
        self.viewer.set_total_frames(total_frames)
        for tr in self.track_widgets:
            tr.set_total_frames(total_frames)
        self.set_frame(0)

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

    def play(self):
        if self.state.playing:
            return
        self.state.playing = True
        self.timer.start()

    def pause(self):
        self.state.playing = False
        self.timer.stop()

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

    @staticmethod
    def _qss():
        return """
        QWidget { background: #121416; color: #E7EDF2; font-family: Segoe UI, Arial; font-size: 12px; }
        #TopBar { background: #0F1113; border: 1px solid #2B343B; border-radius: 10px; }
        #TopTitle { font-weight: 700; letter-spacing: 0.5px; }
        #TopHint { color: #A7B3BD; }

        QFrame#Panel { background: #1A1F23; border: 1px solid #2B343B; border-radius: 10px; }
        QWidget#PanelHeader {
            background: #161B1F; border-bottom: 1px solid #2B343B;
            border-top-left-radius: 10px; border-top-right-radius: 10px;
        }
        QWidget#PanelFooter {
            background: #14181C; border-top: 1px solid #2B343B;
            border-bottom-left-radius: 10px; border-bottom-right-radius: 10px;
        }

        QLabel#Muted { color: #A7B3BD; }
        QLabel#SectionTitle { color: #A7B3BD; font-weight: 700; letter-spacing: 0.3px; }
        QLabel#LayerName { color: #A7B3BD; }
        QLabel#BoldValue { color: #E7EDF2; font-weight: 700; }
        QLabel#FrameBig { font-size: 20px; font-weight: 800; }
        QLabel#FooterNote { color: rgba(255,255,255,0.55); font-size: 11px; }

        QPushButton {
            background: #2A3238; border: 1px solid #2B343B;
            padding: 8px 10px; border-radius: 8px;
        }
        QPushButton:hover { background: #344049; }
        QPushButton#PrimaryButton { border: 1px solid rgba(122,162,255,110); }
        QPushButton#RecentFolderIcon {
            min-width: 28px; max-width: 28px;
            min-height: 28px; max-height: 28px;
            border-radius: 14px;
            padding: 0px;
            font-size: 14px;
        }

        QScrollArea#ScrollArea { border: none; background: transparent; }
        QScrollArea#ScrollArea QWidget { background: transparent; }

        QFrame#ThumbFrame { background: #0C0F12; border: 1px solid #2B343B; border-radius: 10px; }
        """
