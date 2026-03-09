from PySide6.QtCore import QThread, Signal

from app.interface.application import DanceTrackerPort


class PoseStreamWorker(QThread):
    """Runs pose streaming detection off the main thread, frame by frame."""

    finished = Signal(int, bool)  # resolved_count, was_cancelled

    def __init__(
        self,
        app: DanceTrackerPort,
        frames_folder_path: str,
        provider: str = "",
        current_frame: int = 0,
    ) -> None:
        super().__init__()
        self._app = app
        self._frames_folder_path = frames_folder_path
        self._provider = provider
        self._current_frame = current_frame
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        if self._provider:
            self._app.pose_detector.set_active_provider(self._provider)

        resolved_count = 0
        was_cancelled = False
        try:
            resolved_count = self._app.pose_detector.detect_streaming(
                self._frames_folder_path,
                should_cancel=lambda: self._cancelled,
                current_frame=self._current_frame,
            )
            was_cancelled = self._cancelled
        except Exception:
            pass
        self.finished.emit(resolved_count, was_cancelled)
