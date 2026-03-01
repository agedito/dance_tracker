from pathlib import Path

from PySide6.QtCore import QCoreApplication, QObject, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QWidget

from ui.widgets.dialogs import BaseProgressDialog

from app.interface.media import MediaPort

VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}
SEQUENCE_SUFFIXES = {".json"}


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
            if self._is_video(path) or self._is_sequence_metadata(path):
                self._load_with_progress(path)
            else:
                self._media_manager.load(path)
            return True

        return False

    def _load_with_progress(self, path: str) -> None:
        progress = BaseProgressDialog("Loading video...", "Cancel", 0, 100, self._parent_widget())
        progress.setWindowTitle("Processing video")
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

    @staticmethod
    def _is_sequence_metadata(path: str) -> bool:
        source = Path(path)
        return source.is_file() and source.suffix.lower() in SEQUENCE_SUFFIXES
