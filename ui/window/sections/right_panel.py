import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QSplitter, QWidget, QTabWidget, QVBoxLayout

from app.interface.application import DanceTrackerPort
from app.interface.event_bus import EventBus
from app.interface.music import SongMetadata
from ui.widgets.log_widget import LogWidget
from ui.widgets.pose_3d_viewer import Pose3DViewerWidget
from ui.widgets.right_panel_tabs import DataTabWidget, EmbedingsTabWidget, LayerViewersTabWidget, MusicTabWidget, SequencesTabWidget
from ui.window.sections.preferences_manager import PreferencesManager


class RightPanel(QFrame):
    """Single responsibility: display right-side tools grouped in tabs."""

    def __init__(self, preferences: PreferencesManager, app: DanceTrackerPort, event_bus: EventBus):
        super().__init__()
        self._preferences = preferences
        self._app = app
        self._current_folder_path: str | None = None
        self.setObjectName("Panel")

        v = QVBoxLayout(self)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(10)

        tabs = QTabWidget()
        tabs.setMovable(True)
        self.logger_widget = LogWidget(display_ms=5000, history_limit=100)
        self.pose_3d_viewer = Pose3DViewerWidget()
        self.music_tab = MusicTabWidget(
            analyze_music=app.music.analyze_for_sequence,
            get_current_folder=self.current_folder_path,
        )
        self.sequences_tab = SequencesTabWidget(app.media, app.sequences, event_bus)
        self.data_tab = DataTabWidget(app.sequence_data)

        self._tabs = tabs
        self._embedings_tab = EmbedingsTabWidget(
            app=app,
            get_current_folder=self.current_folder_path,
            log_message=self.logger_widget.log,
        )

        self._tab_widgets_by_id: dict[str, QWidget] = {
            "sequences": self.sequences_tab,
            "layer_viewers": LayerViewersTabWidget(),
            "visor_3d": self.pose_3d_viewer,
            "music": self.music_tab,
            "data": self.data_tab,
            "embedings": self._embedings_tab,
        }
        self._tab_labels_by_id: dict[str, str] = {
            "sequences": "Sequences",
            "layer_viewers": "Layer viewers",
            "visor_3d": "Visor 3D",
            "music": "Music",
            "data": "Data",
            "embedings": "Embedings",
        }

        self._add_tabs_in_saved_order()
        tabs.tabBar().tabMoved.connect(self._save_tab_order)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(tabs)
        splitter.addWidget(self.logger_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 200])

        v.addWidget(splitter, 1)

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


    def sync_detectors_from_app(self) -> None:
        self._embedings_tab.load_detectors(
            detector_names=self._app.track_detector.available_detectors(),
            active_detector=self._app.track_detector.active_detector(),
        )



    def set_current_folder_path(self, folder_path: str | None) -> None:
        self._current_folder_path = folder_path

    def current_folder_path(self) -> str | None:
        return self._current_folder_path

    def update_pose(self, frame: int):
        detections = self._mock_yolo_pose_detections(frame)
        self.pose_3d_viewer.set_detections(detections)

    def update_song_info(self, song: SongMetadata):
        self.music_tab.update_song_info(song)


    def update_sequence_data(self, frames_folder_path: str) -> None:
        self.data_tab.update_from_sequence(frames_folder_path)

    def clear_sequence_data(self) -> None:
        self.data_tab.clear()

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
