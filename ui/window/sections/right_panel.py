import math

from PySide6.QtWidgets import (
    QFrame,
    QWidget,
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

    def __init__(
            self,
            preferences: PreferencesManager,
            media_manager: MediaPort,
            on_sequence_removed=None,
    ):
        super().__init__()
        self._preferences = preferences
        self.setObjectName("Panel")

        v = QVBoxLayout(self)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(10)

        tabs = QTabWidget()
        tabs.setMovable(True)
        self.pose_3d_viewer = Pose3DViewerWidget()
        self.music_tab = MusicTabWidget()
        self.sequences_tab = SequencesTabWidget(
            preferences,
            media_manager,
            on_sequence_removed=on_sequence_removed,
        )

        self._tabs = tabs
        self._tab_widgets_by_id: dict[str, QWidget] = {
            "sequences": self.sequences_tab,
            "layer_viewers": LayerViewersTabWidget(),
            "visor_3d": self.pose_3d_viewer,
            "music": self.music_tab,
            "embedings": EmbedingsTabWidget(),
        }
        self._tab_labels_by_id: dict[str, str] = {
            "sequences": "Sequences",
            "layer_viewers": "Layer viewers",
            "visor_3d": "Visor 3D",
            "music": "Music",
            "embedings": "Embedings",
        }

        self._add_tabs_in_saved_order()
        tabs.tabBar().tabMoved.connect(self._save_tab_order)
        v.addWidget(tabs, 1)

    def _add_tabs_in_saved_order(self):
        desired_order = self._preferences.right_panel_tab_order()
        available_ids = list(self._tab_widgets_by_id.keys())

        ordered_ids = [tab_id for tab_id in desired_order if tab_id in available_ids]
        ordered_ids.extend(tab_id for tab_id in available_ids if tab_id not in ordered_ids)

        for tab_id in ordered_ids:
            self._tabs.addTab(self._tab_widgets_by_id[tab_id], self._tab_labels_by_id[tab_id])

    def _save_tab_order(self, *_):
        current_order: list[str] = []
        for i in range(self._tabs.count()):
            widget = self._tabs.widget(i)
            tab_id = next(
                (
                    id_candidate
                    for id_candidate, tab_widget in self._tab_widgets_by_id.items()
                    if tab_widget is widget
                ),
                None,
            )
            if tab_id:
                current_order.append(tab_id)

        self._preferences.save_right_panel_tab_order(current_order)

    def update_pose(self, frame: int):
        detections = self._mock_yolo_pose_detections(frame)
        self.pose_3d_viewer.set_detections(detections)

    def refresh_sequences(self):
        self.sequences_tab.refresh()

    def set_active_sequence(self, folder_path: str | None):
        self.sequences_tab.set_active_folder(folder_path)

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
