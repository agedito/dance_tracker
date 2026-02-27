import math

from PySide6.QtWidgets import (
    QFrame,
    QTabWidget,
    QVBoxLayout,
)

from app.interface.music import SongMetadata
from app.interface.media import MediaPort
from ui.widgets.pose_3d_viewer import Pose3DViewerWidget
from ui.widgets.right_panel_tabs import (
    EmbedingsTabWidget,
    LayerViewersTabWidget,
    MusicTabWidget,
    SequencesTabWidget,
)
from ui.window.sections.preferences_manager import PreferencesManager


class RightPanel(QFrame):
    """Single responsibility: display right-side tools grouped in tabs."""

    def __init__(self, preferences: PreferencesManager, media_manager: MediaPort):
        super().__init__()
        self.setObjectName("Panel")

        v = QVBoxLayout(self)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(10)

        tabs = QTabWidget()
        tabs.addTab(LayerViewersTabWidget(), "Layer viewers")

        self.pose_3d_viewer = Pose3DViewerWidget()
        self.music_tab = MusicTabWidget()
        self.sequences_tab = SequencesTabWidget(preferences, media_manager)

        tabs.addTab(self.pose_3d_viewer, "Visor 3D")
        tabs.addTab(self.music_tab, "Music")
        tabs.addTab(EmbedingsTabWidget(), "Embedings")
        tabs.addTab(self.sequences_tab, "Sequences")
        v.addWidget(tabs, 1)

    def update_pose(self, frame: int):
        detections = self._mock_yolo_pose_detections(frame)
        self.pose_3d_viewer.set_detections(detections)

    def refresh_sequences(self):
        self.sequences_tab.refresh()

    def update_song_info(self, song: SongMetadata):
        self.music_tab.update_song_info(song)

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
