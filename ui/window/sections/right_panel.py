import math
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.pose_3d_viewer import Pose3DViewerWidget
from ui.widgets.thumbnail import ThumbnailWidget
from ui.window.sections.preferences_manager import PreferencesManager


class RightPanel(QFrame):
    """Single responsibility: display right-side tools grouped in tabs."""

    def __init__(self, preferences: PreferencesManager, on_media_selected: Callable[[str], None]):
        super().__init__()
        self._prefs = preferences
        self._on_media_selected = on_media_selected
        self.setObjectName("Panel")

        v = QVBoxLayout(self)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(10)

        tabs = QTabWidget()
        tabs.addTab(self._build_layer_viewers_tab(), "Layer viewers")

        self.pose_3d_viewer = Pose3DViewerWidget()
        tabs.addTab(self.pose_3d_viewer, "Visor 3D")
        tabs.addTab(self._build_music_tab(), "Music")
        tabs.addTab(self._build_sequences_tab(), "Sequences")
        v.addWidget(tabs, 1)

    def update_pose(self, frame: int):
        detections = self._mock_yolo_pose_detections(frame)
        self.pose_3d_viewer.set_detections(detections)

    def refresh_sequences(self):
        self._rebuild_sequences_grid()

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionTitle")
        return label

    def _build_layer_viewers_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(self._section_label("LAYER VIEWERS"))
        grid1 = QGridLayout()
        grid1.setSpacing(8)
        grid1.addWidget(self._thumb("Layer 1: Color Grade", 10), 0, 0)
        grid1.addWidget(self._thumb("Layer 1: Output", 17), 0, 1)
        layout.addLayout(grid1)

        layout.addWidget(self._section_label("LAYER 2: OBJECT MASK"))
        grid2 = QGridLayout()
        grid2.setSpacing(8)
        grid2.addWidget(self._thumb("Layer 2: Mask", 24), 0, 0)
        grid2.addWidget(self._thumb("Layer 2: Overlay", 31), 0, 1)
        layout.addLayout(grid2)

        footer = QLabel("Mock: thumbnails procedural + poses YOLO 3D.")
        footer.setObjectName("FooterNote")
        layout.addWidget(footer)
        layout.addStretch(1)
        return tab

    def _build_music_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._section_label("Music"))
        layout.addStretch(1)
        return tab

    def _build_sequences_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        load_btn = QPushButton("Cargar video")
        load_btn.clicked.connect(self._pick_video)
        layout.addWidget(load_btn)

        self._seq_scroll = QScrollArea()
        self._seq_scroll.setObjectName("ScrollArea")
        self._seq_scroll.setWidgetResizable(True)
        self._seq_container = QWidget()
        self._seq_grid = QGridLayout(self._seq_container)
        self._seq_grid.setSpacing(10)
        self._seq_grid.setContentsMargins(0, 0, 0, 0)
        self._seq_scroll.setWidget(self._seq_container)
        layout.addWidget(self._seq_scroll, 1)

        self._rebuild_sequences_grid()
        return tab

    def _pick_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecciona un video",
            "",
            "Videos (*.mp4 *.mov *.avi *.mkv *.webm *.m4v);;Todos (*.*)",
        )
        if file_path:
            self._on_media_selected(file_path)

    def _rebuild_sequences_grid(self):
        while self._seq_grid.count():
            item = self._seq_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        folders = list(reversed(self._prefs.recent_folders()))
        for idx, folder in enumerate(folders):
            button = self._sequence_button(folder)
            row, col = divmod(idx, 2)
            self._seq_grid.addWidget(button, row, col)

        if not folders:
            empty = QLabel("Aún no hay secuencias recientes.")
            empty.setObjectName("Muted")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._seq_grid.addWidget(empty, 0, 0, 1, 2)

    def _sequence_button(self, folder_path: str) -> QPushButton:
        p = Path(folder_path).expanduser()
        button = QPushButton(p.name)
        button.setToolTip(folder_path)
        button.setFixedSize(QSize(140, 100))
        button.clicked.connect(lambda _=False, path=folder_path: self._on_media_selected(path))

        thumbnail = self._prefs.thumbnail_for_folder(folder_path)
        if thumbnail:
            button.setIcon(QIcon(thumbnail))
            button.setIconSize(QSize(128, 72))
        return button

    @staticmethod
    def _thumb(label: str, seed: int) -> QFrame:
        f = QFrame()
        f.setObjectName("ThumbFrame")
        layout = QVBoxLayout(f)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(ThumbnailWidget(label, seed))
        return f

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
