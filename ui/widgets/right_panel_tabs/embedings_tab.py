from collections.abc import Callable

from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.interface.application import DanceTrackerPort
from app.interface.track_detector import CapabilityInfo
from ui.widgets.detection_stream_worker import DetectionStreamWorker
from ui.widgets.generic_widgets.detection_group import DetectionGroupWidget
from ui.widgets.pose_stream_worker import PoseStreamWorker
from ui.widgets.right_panel_tabs.common import section_label
from ui.window.sections.preferences_manager import PreferencesManager

_STREAMING_CAPABLE_PROVIDERS = frozenset({"rtdetr", "mediapipe"})

# Capability keys in display order
_CAPABILITY_ORDER = ["detection", "pose", "segmentation"]
_GROUP_TITLES = {
    "detection": "Detections",
    "pose": "Pose",
    "segmentation": "Segmentation",
}


class EmbeddingsTabWidget(QWidget):
    def __init__(
            self,
            app: DanceTrackerPort,
            get_current_folder: Callable[[], str | None],
            log_message: Callable[[str], None],
            preferences: PreferencesManager,
    ):
        super().__init__()
        self._app = app
        self._get_current_folder = get_current_folder
        self._log_message = log_message
        self._preferences = preferences

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(section_label("Embeddings"))

        capabilities = app.track_detector.service_capabilities()
        self._groups: dict[str, DetectionGroupWidget] = {}

        for key in _CAPABILITY_ORDER:
            cap: CapabilityInfo | None = capabilities.get(key)
            title = _GROUP_TITLES.get(key, key.capitalize())
            is_detection = key == "detection"
            is_pose = key == "pose"
            saved = preferences.embeddings_group_state(key)

            group = DetectionGroupWidget(
                title=title,
                capability=cap,
                get_current_folder=get_current_folder,
                log_message=log_message,
                on_detector_changed=self._on_detector_changed if is_detection else None,
                on_detect=self._make_detect_fn() if is_detection else (self._make_pose_detect_fn() if is_pose else None),
                on_clean=self._on_clean_detections if is_detection else (self._on_clean_poses if is_pose else None),
                create_stream_worker=self._make_stream_worker if is_detection else (self._make_pose_stream_worker if is_pose else None),
                on_state_changed=self._make_state_changed_fn(key),
                initial_provider=saved.get("provider", ""),
                initial_endpoint=saved.get("endpoint", ""),
                initial_single_per_frame=bool(saved.get("single_per_frame", False)),
            )
            self._groups[key] = group
            layout.addWidget(group)

        layout.addStretch(1)

    # ── Public ────────────────────────────────────────────────────────

    def sync_selected_detector(self) -> None:
        detection_group = self._groups.get("detection")
        if detection_group:
            detection_group.sync_provider(self._app.track_detector.active_detector())

    # ── Private ───────────────────────────────────────────────────────

    def _on_detector_changed(self, provider: str) -> None:
        if not provider:
            return
        if self._app.track_detector.set_active_detector(provider):
            self._log_message(f"Detector selected: {provider}.")
        else:
            self._log_message(f"Unable to select detector: {provider}.")

    def _make_detect_fn(self) -> Callable[[str, str, str], int]:
        def _detect(folder: str, provider: str, endpoint_type: str) -> int:
            self._app.track_detector.set_active_detector(provider)
            if endpoint_type == "single":
                return self._app.track_detector.detect_people_for_sequence(
                    folder, frame_index=self._app.frames.cur_frame
                )
            if endpoint_type == "batch":
                return self._app.track_detector.detect_people_for_sequence(folder)
            if endpoint_type == "video":
                return self._app.track_detector.detect_people_for_video(folder)
            return 0
        return _detect

    def _on_clean_detections(self, folder: str, _provider: str) -> None:
        self._app.track_detector.clear_detections(folder)
        self._log_message("Detections cleared.")

    def _make_pose_detect_fn(self) -> Callable[[str, str, str], int]:
        def _detect(folder: str, provider: str, endpoint_type: str) -> int:
            self._app.pose_detector.set_active_provider(provider)
            if endpoint_type == "single":
                return self._app.pose_detector.detect_for_sequence(
                    folder, frame_index=self._app.frames.cur_frame
                )
            if endpoint_type == "batch":
                return self._app.pose_detector.detect_for_sequence(folder)
            if endpoint_type == "video":
                return self._app.pose_detector.detect_for_video(folder)
            return 0
        return _detect

    def _on_clean_poses(self, folder: str, _provider: str) -> None:
        self._app.pose_detector.clear_poses(folder)
        self._log_message("Poses cleared.")

    def _make_pose_stream_worker(self, folder: str, provider: str) -> PoseStreamWorker:
        return PoseStreamWorker(
            self._app,
            folder,
            provider=provider,
            current_frame=self._app.frames.cur_frame,
        )

    def _make_stream_worker(self, folder: str, provider: str) -> DetectionStreamWorker:
        return DetectionStreamWorker(
            self._app,
            folder,
            provider=provider,
            current_frame=self._app.frames.cur_frame,
        )

    def _make_state_changed_fn(self, group_key: str) -> Callable[[str, str, bool], None]:
        def _save(provider: str, endpoint: str, single_per_frame: bool) -> None:
            self._preferences.save_embeddings_group_state(
                group_key, provider, endpoint, single_per_frame
            )
        return _save
