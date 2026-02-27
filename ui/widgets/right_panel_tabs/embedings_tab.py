from collections.abc import Callable

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from app.interface.application import DanceTrackerPort
from ui.widgets.right_panel_tabs.common import section_label


class EmbedingsTabWidget(QWidget):
    def __init__(
        self,
        app: DanceTrackerPort,
        get_current_folder: Callable[[], str | None],
        log_message: Callable[[str], None],
    ):
        super().__init__()
        self._app = app
        self._get_current_folder = get_current_folder
        self._log_message = log_message

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section_label("Embedings"))

        info = QLabel("Run a mock person detector over all loaded frames.")
        info.setWordWrap(True)
        layout.addWidget(info)

        self._detect_button = QPushButton("Detect people")
        self._detect_button.clicked.connect(self._on_detect_people_clicked)
        layout.addWidget(self._detect_button)

        layout.addStretch(1)

    def _on_detect_people_clicked(self) -> None:
        frames_folder_path = self._get_current_folder()
        if not frames_folder_path:
            self._log_message("No sequence loaded. Load a sequence before running detection.")
            return

        self._log_message("Person detection started.")
        total_frames = self._app.track_detector.detect_people_for_sequence(frames_folder_path)
        self._log_message(f"Person detection finished. Processed {total_frames} frames.")
