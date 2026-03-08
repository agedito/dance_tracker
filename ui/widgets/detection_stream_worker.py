from PySide6.QtCore import QThread, Signal

from app.interface.application import DanceTrackerPort


class DetectionStreamWorker(QThread):
    """QThread that runs streaming detection without blocking the Qt main thread.

    Calls app.track_detector.detect_people_streaming() which emits
    DetectionStarted / DetectionFrameResolved / DetectionsUpdated events via the
    EventBus for each frame.  The worker only signals back its own completion state
    so EmbeddingsTabWidget can update its local controls.
    """

    finished = Signal(int, bool)  # (resolved_frame_count, was_cancelled)

    def __init__(self, app: DanceTrackerPort, frames_folder_path: str, current_frame: int = 0) -> None:
        super().__init__()
        self._app = app
        self._frames_folder_path = frames_folder_path
        self._current_frame = current_frame
        self._cancel_requested = False

    def cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:
        count = 0
        try:
            count = self._app.track_detector.detect_people_streaming(
                self._frames_folder_path,
                should_cancel=lambda: self._cancel_requested,
                current_frame=self._current_frame,
            )
        except Exception:
            pass
        self.finished.emit(count, self._cancel_requested)
