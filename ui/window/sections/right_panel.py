from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QSplitter, QTabWidget, QVBoxLayout, QWidget

from app.interface.application import DanceTrackerPort
from app.interface.event_bus import EventBus
from app.interface.music import SongMetadata
from ui.widgets.log_widget import LogWidget
from ui.widgets.pose_3d_viewer import Pose3DViewerWidget
from ui.widgets.right_panel_tabs import DataTabWidget, EmbedingsTabWidget, LayerViewersTabWidget, MusicTabWidget, SequencesTabWidget
from ui.window.sections.preferences_manager import PreferencesManager


class _TabOrderManager:
    """Restores and persists the drag-reorder position of each tab."""

    def __init__(
        self,
        tabs: QTabWidget,
        widgets: dict[str, QWidget],
        labels: dict[str, str],
        preferences: PreferencesManager,
    ):
        self._tabs = tabs
        self._widgets = widgets
        self._labels = labels
        self._preferences = preferences
        self._add_in_saved_order()
        tabs.tabBar().tabMoved.connect(self._save_order)

    def _add_in_saved_order(self) -> None:
        desired_order = self._preferences.right_panel_tab_order()
        available_ids = list(self._widgets.keys())
        ordered_ids = [tab_id for tab_id in desired_order if tab_id in available_ids]
        ordered_ids.extend(tab_id for tab_id in available_ids if tab_id not in ordered_ids)
        for tab_id in ordered_ids:
            self._tabs.addTab(self._widgets[tab_id], self._labels[tab_id])

    def _save_order(self, *_) -> None:
        current_order: list[str] = []
        for i in range(self._tabs.count()):
            widget = self._tabs.widget(i)
            tab_id = next(
                (id_ for id_, w in self._widgets.items() if w is widget),
                None,
            )
            if tab_id:
                current_order.append(tab_id)
        self._preferences.save_right_panel_tab_order(current_order)


class RightPanel(QFrame):
    def __init__(self, preferences: PreferencesManager, app: DanceTrackerPort, event_bus: EventBus):
        super().__init__()
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

        tab_widgets: dict[str, QWidget] = {
            "sequences": self.sequences_tab,
            "layer_viewers": LayerViewersTabWidget(),
            "visor_3d": self.pose_3d_viewer,
            "music": self.music_tab,
            "data": self.data_tab,
            "embedings": EmbedingsTabWidget(
                app=app,
                get_current_folder=self.current_folder_path,
                log_message=self.logger_widget.log,
            ),
        }
        tab_labels: dict[str, str] = {
            "sequences": "Sequences",
            "layer_viewers": "Layer viewers",
            "visor_3d": "Visor 3D",
            "music": "Music",
            "data": "Data",
            "embedings": "Embedings",
        }

        self._tab_order_manager = _TabOrderManager(tabs, tab_widgets, tab_labels, preferences)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(tabs)
        splitter.addWidget(self.logger_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 200])

        v.addWidget(splitter, 1)

    def set_current_folder_path(self, folder_path: str | None) -> None:
        self._current_folder_path = folder_path

    def current_folder_path(self) -> str | None:
        return self._current_folder_path

    def update_pose(self, frame: int) -> None:
        self.pose_3d_viewer.set_frame_for_demo(frame)

    def update_song_info(self, song: SongMetadata) -> None:
        self.music_tab.update_song_info(song)

    def update_sequence_data(self, frames_folder_path: str) -> None:
        self.data_tab.update_from_sequence(frames_folder_path)

    def clear_sequence_data(self) -> None:
        self.data_tab.clear()
