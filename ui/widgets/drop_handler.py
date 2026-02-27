from PySide6.QtCore import QCoreApplication, QObject, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from pathlib import Path

from PySide6.QtWidgets import QProgressDialog, QWidget

from app.interface.media import MediaPort

VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}


class DropHandler(QObject):
    """Single responsibility: handle drag-and-drop of folders/videos onto the viewer."""

    folderLoaded = Signal(str, int)
    framesLoaded = Signal(int)

    def __init__(self, media_manager: MediaPort, parent: QObject | None = None):
        super().__init__(parent)
        self._media_manager = media_manager

    @staticmethod
    def can_accept(ev: QDragEnterEvent) -> bool:
        if ev.mimeData().hasUrls():
            return any(url.isLocalFile() for url in ev.mimeData().urls())
        return False

    def handle_drop(self, ev: QDropEvent) -> bool:
        for url in ev.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if self._is_video(path):
                self._load_with_progress(path)
            else:
                self._media_manager.load(path)
            return True

        return False

    def _load_with_progress(self, path: str) -> None:
        progress = QProgressDialog("Cargando video...", "Cancelar", 0, 100, self._parent_widget())
        progress.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        progress.setWindowTitle("Procesando video")
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(True)
        progress.setValue(0)
        progress.show()

        def on_progress(value: int) -> None:
            progress.setValue(max(0, min(100, value)))
            QCoreApplication.processEvents()

        self._media_manager.load(path, on_progress=on_progress, should_cancel=progress.wasCanceled)
        progress.close()

    def _parent_widget(self) -> QWidget | None:
        parent = self.parent()
        if isinstance(parent, QWidget):
            return parent
        return None


    @staticmethod
    def _is_video(path: str) -> bool:
        source = Path(path)
        return source.is_file() and source.suffix.lower() in VIDEO_SUFFIXES
