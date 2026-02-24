from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from app.interface.media import MediaPort


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
            self._media_manager.load(path)

            return True

        return False
