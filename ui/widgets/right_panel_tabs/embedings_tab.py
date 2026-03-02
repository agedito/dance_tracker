from collections.abc import Callable

from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

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

        info = QLabel("Run a person detector over loaded frames.")
        info.setWordWrap(True)
        layout.addWidget(info)

        controls_layout = QHBoxLayout()

        self._detectors_combo = QComboBox()
        self._detectors_combo.addItems(self._app.track_detector.available_detectors())
        active_detector = self._app.track_detector.active_detector()
        active_index = self._detectors_combo.findText(active_detector)
        if active_index >= 0:
            self._detectors_combo.setCurrentIndex(active_index)
        self._detectors_combo.currentTextChanged.connect(self._on_detector_changed)
        controls_layout.addWidget(self._detectors_combo, 1)

        self._detect_current_frame_checkbox = QCheckBox("Current frame only")
        controls_layout.addWidget(self._detect_current_frame_checkbox)

        self._detect_button = QPushButton("Detect people")
        self._detect_button.clicked.connect(self._on_detect_people_clicked)
        controls_layout.addWidget(self._detect_button)

        layout.addLayout(controls_layout)
        layout.addStretch(1)

    def _set_detection_controls_enabled(self, enabled: bool) -> None:
        self._detect_button.setEnabled(enabled)
        self._detectors_combo.setEnabled(enabled)
        self._detect_current_frame_checkbox.setEnabled(enabled)

    def _on_detector_changed(self, detector_name: str) -> None:
        if not detector_name:
            return
        if self._app.track_detector.set_active_detector(detector_name):
            self._log_message(f"Detector selected: {detector_name}.")
            return
        self._log_message(f"Unable to select detector: {detector_name}.")

    def _on_detect_people_clicked(self) -> None:
        frames_folder_path = self._get_current_folder()
        if not frames_folder_path:
            self._log_message("No sequence loaded. Load a sequence before running detection.")
            return

        detector_name = self._app.track_detector.active_detector()
        detect_current_only = self._detect_current_frame_checkbox.isChecked()
        if detect_current_only:
            frame_index = self._app.frames.cur_frame
            self._log_message(
                f"Person detection started with detector: {detector_name}. Current frame mode at frame {frame_index}."
            )
            processed = self._app.track_detector.detect_people_for_sequence(frames_folder_path, frame_index=frame_index)
            self._log_message(f"Person detection finished. Processed {processed} frame.")
            return

        self._set_detection_controls_enabled(False)
        self._log_message(f"Person detection started with detector: {detector_name}.")
        processed = self._app.track_detector.detect_people_for_sequence(frames_folder_path)
        self._set_detection_controls_enabled(True)
        self._log_message(f"Person detection finished. Processed {processed} frames.")
