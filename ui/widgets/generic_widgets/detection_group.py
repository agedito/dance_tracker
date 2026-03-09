"""Reusable detection-controls group box.

Layout per group:
  [provider combo] [endpoint combo] [☐ single per frame (batch only)] [Detect] [Cancel]

Endpoint behaviour:
  single → on_detect(folder, provider, "single")   (current frame)
  batch  → if single_per_frame checked → streaming worker (single endpoint per frame)
           else                         → on_detect(folder, provider, "batch")
  video  → on_detect(folder, provider, "video")

State (provider, endpoint, single_per_frame) is persisted via on_state_changed callback.
"""

import time
from collections.abc import Callable

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QPushButton

from app.interface.track_detector import CapabilityInfo
from PySide6.QtCore import QThread

from ui.widgets.detection_stream_worker import DetectionStreamWorker


class _DetectWorker(QThread):
    """Runs a single blocking on_detect call off the main thread."""

    finished = Signal(int)  # processed_count

    def __init__(self, fn: Callable[[], int]) -> None:
        super().__init__()
        self._fn = fn

    def run(self) -> None:
        count = 0
        try:
            count = self._fn()
        except Exception:
            pass
        self.finished.emit(count)


class DetectionGroupWidget(QGroupBox):
    def __init__(
        self,
        title: str,
        capability: CapabilityInfo | None,
        get_current_folder: Callable[[], str | None],
        log_message: Callable[[str], None],
        on_detector_changed: Callable[[str], None] | None = None,
        on_detect: Callable[[str, str, str], int] | None = None,
        on_clean: Callable[[str, str], None] | None = None,
        create_stream_worker: Callable[[str, str], QThread] | None = None,
        on_state_changed: Callable[[str, str, bool], None] | None = None,
        initial_provider: str = "",
        initial_endpoint: str = "",
        initial_single_per_frame: bool = False,
    ):
        """
        Args:
            title: Group box label.
            capability: Parsed capability info (providers + endpoints). None → empty/disabled.
            get_current_folder: Returns the currently loaded frames folder path or None.
            log_message: Append a line to the log widget.
            on_detector_changed: Called when the provider combo changes.
            on_detect: Called for non-streaming detections.
                       Signature: (folder, provider, endpoint_type) -> processed_count.
                       None = not connected (clicks log "not connected yet").
            create_stream_worker: Factory for streaming worker (batch + single_per_frame mode).
                       Signature: (folder, provider) -> QThread with finished(int, bool) signal and cancel().
            on_state_changed: Persist (provider, endpoint, single_per_frame) on any change.
            initial_provider: Provider to pre-select (from saved prefs).
            initial_endpoint: Endpoint to pre-select (from saved prefs).
            initial_single_per_frame: Checkbox initial state (from saved prefs).
        """
        super().__init__(title)
        self._capability = capability
        self._get_current_folder = get_current_folder
        self._log_message = log_message
        self._on_detector_changed_cb = on_detector_changed
        self._on_detect = on_detect
        self._on_clean = on_clean
        self._create_stream_worker = create_stream_worker
        self._on_state_changed = on_state_changed
        self._stream_worker: QThread | None = None
        self._detect_worker: _DetectWorker | None = None
        self._detection_start_time: float = 0.0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(6)

        # ── Provider combo ────────────────────────────────────────────
        self._provider_combo = QComboBox()
        if capability:
            self._provider_combo.addItems(capability.providers)
        self._provider_combo.currentTextChanged.connect(self._on_provider_changed)
        layout.addWidget(self._provider_combo, 1)

        # ── Single-per-frame checkbox (batch mode only, always reserves space) ──
        self._single_per_frame_check = QCheckBox("single per frame")
        self._single_per_frame_check.setChecked(initial_single_per_frame)
        self._single_per_frame_check.toggled.connect(self._on_single_per_frame_toggled)
        self._single_per_frame_check.setVisible(False)
        sp = self._single_per_frame_check.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self._single_per_frame_check.setSizePolicy(sp)
        layout.addWidget(self._single_per_frame_check)

        # ── Endpoint combo ────────────────────────────────────────────
        self._endpoint_combo = QComboBox()
        self._endpoint_combo.currentTextChanged.connect(self._on_endpoint_changed)
        layout.addWidget(self._endpoint_combo)

        # ── Detect button ─────────────────────────────────────────────
        self._detect_button = QPushButton("Detect")
        self._detect_button.clicked.connect(self._on_detect_clicked)
        layout.addWidget(self._detect_button)

        self._clean_button = QPushButton("Clean")
        self._clean_button.clicked.connect(self._on_clean_clicked)
        layout.addWidget(self._clean_button)

        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.setVisible(False)
        self._cancel_button.clicked.connect(self._on_cancel_clicked)
        layout.addWidget(self._cancel_button)

        # ── Enable/disable based on providers ─────────────────────────
        has_providers = bool(capability and capability.providers)
        self._provider_combo.setEnabled(has_providers)
        self._endpoint_combo.setEnabled(has_providers)
        self._detect_button.setEnabled(has_providers)
        self._clean_button.setEnabled(has_providers)

        # ── Restore saved state ───────────────────────────────────────
        self._restore_state(initial_provider, initial_endpoint)

    # ── Public ────────────────────────────────────────────────────────

    def sync_provider(self, provider_name: str) -> None:
        """Update the provider combo to reflect an externally-set active provider."""
        idx = self._provider_combo.findText(provider_name)
        if idx < 0 or self._provider_combo.currentIndex() == idx:
            return
        self._provider_combo.blockSignals(True)
        self._provider_combo.setCurrentIndex(idx)
        self._provider_combo.blockSignals(False)
        self._refresh_endpoint_combo(keep_current=True)

    def current_provider(self) -> str:
        return self._provider_combo.currentText()

    def current_endpoint(self) -> str:
        return self._endpoint_combo.currentText()

    # ── Internal ──────────────────────────────────────────────────────

    def _restore_state(self, initial_provider: str, initial_endpoint: str) -> None:
        """Populate endpoint combo then apply saved provider/endpoint selections."""
        self._refresh_endpoint_combo(keep_current=False)

        if initial_provider:
            idx = self._provider_combo.findText(initial_provider)
            if idx >= 0:
                self._provider_combo.blockSignals(True)
                self._provider_combo.setCurrentIndex(idx)
                self._provider_combo.blockSignals(False)
                self._refresh_endpoint_combo(keep_current=False)

        if initial_endpoint:
            idx = self._endpoint_combo.findText(initial_endpoint)
            if idx >= 0:
                self._endpoint_combo.blockSignals(True)
                self._endpoint_combo.setCurrentIndex(idx)
                self._endpoint_combo.blockSignals(False)

        self._update_checkbox_visibility()

    def _refresh_endpoint_combo(self, keep_current: bool = True) -> None:
        """Rebuild endpoint combo to only show endpoints the current provider supports."""
        prev = self._endpoint_combo.currentText() if keep_current else ""
        self._endpoint_combo.blockSignals(True)
        self._endpoint_combo.clear()
        if self._capability:
            provider = self._provider_combo.currentText()
            for ep_key, ep_info in self._capability.endpoints.items():
                if not provider or provider in ep_info.providers:
                    self._endpoint_combo.addItem(ep_key)
        if prev:
            idx = self._endpoint_combo.findText(prev)
            if idx >= 0:
                self._endpoint_combo.setCurrentIndex(idx)
        self._endpoint_combo.blockSignals(False)
        self._update_checkbox_visibility()

    def _update_checkbox_visibility(self) -> None:
        self._single_per_frame_check.setVisible(
            self._endpoint_combo.currentText() == "batch"
        )

    def _uses_streaming(self) -> bool:
        return (
            self._endpoint_combo.currentText() == "batch"
            and self._single_per_frame_check.isChecked()
            and self._create_stream_worker is not None
        )

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._detect_button.setEnabled(enabled)
        self._clean_button.setEnabled(enabled)
        self._provider_combo.setEnabled(enabled)
        self._endpoint_combo.setEnabled(enabled)
        if enabled:
            self._update_checkbox_visibility()
        else:
            self._single_per_frame_check.setVisible(False)

    def _emit_state(self) -> None:
        if self._on_state_changed:
            self._on_state_changed(
                self._provider_combo.currentText(),
                self._endpoint_combo.currentText(),
                self._single_per_frame_check.isChecked(),
            )

    # ── Slots ─────────────────────────────────────────────────────────

    def _on_provider_changed(self, provider: str) -> None:
        self._refresh_endpoint_combo(keep_current=True)
        if self._on_detector_changed_cb:
            self._on_detector_changed_cb(provider)
        self._emit_state()

    def _on_endpoint_changed(self, _endpoint: str) -> None:
        self._update_checkbox_visibility()
        self._emit_state()

    def _on_single_per_frame_toggled(self, _checked: bool) -> None:
        self._emit_state()

    def _on_detect_clicked(self) -> None:
        folder = self._get_current_folder()
        if not folder:
            self._log_message("No sequence loaded.")
            return

        provider = self._provider_combo.currentText()
        endpoint = self._endpoint_combo.currentText()

        if self._on_detect is None:
            self._log_message(f"[{self.title()}] not connected yet.")
            return

        if self._uses_streaming():
            self._start_streaming(folder, provider)
            return

        self._start_detect(folder, provider, endpoint)

    def _start_detect(self, folder: str, provider: str, endpoint: str) -> None:
        self._log_message(f"Detection started [{provider}/{endpoint}].")
        self._set_controls_enabled(False)
        self._detection_start_time = time.monotonic()

        fn = self._on_detect
        worker = _DetectWorker(lambda: fn(folder, provider, endpoint))
        worker.finished.connect(self._on_detect_worker_finished)
        self._detect_worker = worker
        worker.start()

    def _on_detect_worker_finished(self, count: int) -> None:
        elapsed = time.monotonic() - self._detection_start_time
        self._detect_worker = None
        self._set_controls_enabled(True)
        provider = self._provider_combo.currentText()
        endpoint = self._endpoint_combo.currentText()
        self._log_message(
            f"Detection finished [{provider}/{endpoint}]. "
            f"Processed {count} frames · {elapsed:.2f}s."
        )

    def _start_streaming(self, folder: str, provider: str) -> None:
        self._log_message(f"Streaming detection started [{provider}/single×frame].")
        self._set_controls_enabled(False)
        self._cancel_button.setVisible(True)
        self._detection_start_time = time.monotonic()

        worker = self._create_stream_worker(folder, provider)
        worker.finished.connect(self._on_worker_finished)
        self._stream_worker = worker
        worker.start()

    def _on_clean_clicked(self) -> None:
        folder = self._get_current_folder()
        if not folder:
            self._log_message("No sequence loaded.")
            return
        if self._on_clean is None:
            self._log_message(f"[{self.title()}] clean not connected.")
            return
        provider = self._provider_combo.currentText()
        self._on_clean(folder, provider)

    def _on_cancel_clicked(self) -> None:
        if self._stream_worker:
            self._stream_worker.cancel()

    def _on_worker_finished(self, resolved_count: int, was_cancelled: bool) -> None:
        elapsed = time.monotonic() - self._detection_start_time
        self._stream_worker = None
        self._cancel_button.setVisible(False)
        self._set_controls_enabled(True)
        status = "cancelled" if was_cancelled else "finished"
        fps = f" ({resolved_count / elapsed:.2f} fps)" if elapsed > 0 else ""
        self._log_message(
            f"Streaming detection {status}. Frames: {resolved_count} · Time: {elapsed:.2f}s.{fps}"
        )
