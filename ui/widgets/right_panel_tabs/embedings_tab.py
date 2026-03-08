import time
from collections.abc import Callable

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.interface.application import DanceTrackerPort
from ui.widgets.detection_stream_worker import DetectionStreamWorker
from ui.widgets.right_panel_tabs.common import section_label

_MODE_FRAME = "Frame"
_MODE_SEQUENCE = "Sequence"
_MODE_VIDEO = "Video"

# Detectors that support sequential /detect streaming via the single-frame endpoint.
_STREAMING_CAPABLE_DETECTORS = frozenset({"rtdetr", "mediapipe"})


class EmbeddingsTabWidget(QWidget):
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
        self._stream_worker: DetectionStreamWorker | None = None
        self._detection_start_time: float = 0.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section_label("Embeddings"))

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

        self._mode_combo = QComboBox()
        self._mode_combo.addItems([_MODE_FRAME, _MODE_SEQUENCE, _MODE_VIDEO])
        controls_layout.addWidget(self._mode_combo)

        self._detect_button = QPushButton("Detect people")
        self._detect_button.clicked.connect(self._on_detect_people_clicked)
        controls_layout.addWidget(self._detect_button)

        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.setVisible(False)
        self._cancel_button.clicked.connect(self._on_cancel_clicked)
        controls_layout.addWidget(self._cancel_button)

        layout.addLayout(controls_layout)
        layout.addStretch(1)

    # ── Public ───────────────────────────────────────────────────────

    def sync_selected_detector(self) -> None:
        active_detector = self._app.track_detector.active_detector()
        active_index = self._detectors_combo.findText(active_detector)
        if active_index < 0:
            return

        if self._detectors_combo.currentIndex() == active_index:
            return

        self._detectors_combo.blockSignals(True)
        self._detectors_combo.setCurrentIndex(active_index)
        self._detectors_combo.blockSignals(False)

    # ── Private helpers ──────────────────────────────────────────────

    def _uses_streaming(self) -> bool:
        mode = self._mode_combo.currentText()
        detector = self._app.track_detector.active_detector()
        return mode == _MODE_SEQUENCE and detector in _STREAMING_CAPABLE_DETECTORS

    def _set_detection_controls_enabled(self, enabled: bool) -> None:
        self._detect_button.setEnabled(enabled)
        self._detectors_combo.setEnabled(enabled)
        self._mode_combo.setEnabled(enabled)

    # ── Slots ────────────────────────────────────────────────────────

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
        mode = self._mode_combo.currentText()

        if mode == _MODE_FRAME:
            frame_index = self._app.frames.cur_frame
            self._log_message(f"Detection started [{detector_name}] — frame {frame_index}.")
            processed = self._app.track_detector.detect_people_for_sequence(
                frames_folder_path, frame_index=frame_index
            )
            self._log_message(f"Detection finished. Processed {processed} frame.")
            return

        if mode == _MODE_SEQUENCE and self._uses_streaming():
            self._start_streaming_detection(frames_folder_path, detector_name)
            return

        self._set_detection_controls_enabled(False)
        if mode == _MODE_VIDEO:
            self._log_message(f"Detection started [{detector_name}] — video mode.")
            processed = self._app.track_detector.detect_people_for_video(frames_folder_path)
        else:
            self._log_message(f"Detection started [{detector_name}] — sequence mode.")
            processed = self._app.track_detector.detect_people_for_sequence(frames_folder_path)
        self._set_detection_controls_enabled(True)
        self._log_message(f"Detection finished. Processed {processed} frames.")

    def _start_streaming_detection(self, frames_folder_path: str, detector_name: str) -> None:
        self._log_message(f"Streaming detection started [{detector_name}] — sequence mode.")
        self._set_detection_controls_enabled(False)
        self._cancel_button.setVisible(True)
        self._detection_start_time = time.monotonic()

        worker = DetectionStreamWorker(self._app, frames_folder_path)
        worker.finished.connect(self._on_worker_finished)
        self._stream_worker = worker
        worker.start()

    def _on_cancel_clicked(self) -> None:
        if self._stream_worker:
            self._stream_worker.cancel()

    def _on_worker_finished(self, resolved_count: int, was_cancelled: bool) -> None:
        elapsed = time.monotonic() - self._detection_start_time
        self._stream_worker = None
        self._cancel_button.setVisible(False)
        self._set_detection_controls_enabled(True)
        status = "cancelled" if was_cancelled else "finished"
        self._log_message(
            f"Streaming detection {status}. "
            f"Frames: {resolved_count} · Time: {elapsed:.2f}s. ({resolved_count / elapsed:.2f} fps)"
        )
