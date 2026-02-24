from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from app.frame_state.frame_store import FrameStore


class DropHandler(QObject):
    """Single responsibility: handle drag-and-drop of folders/videos onto the viewer."""

    folderLoaded = Signal(str, int)
    framesLoaded = Signal(int)

    def __init__(self, frame_store: FrameStore, parent: QObject | None = None):
        super().__init__(parent)
        self._frame_store = frame_store

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

            # Try video extraction first
            frames_folder, extracted = self._frame_store.extract_video_frames(path)
            if extracted > 0 and frames_folder is not None:
                loaded = self._frame_store.load_folder(frames_folder)
                if loaded > 0:
                    self.framesLoaded.emit(loaded)
                    self.folderLoaded.emit(frames_folder, loaded)
                    return True

            # Fall back to loading as the frame folder
            loaded = self._frame_store.load_folder(path)
            if loaded > 0:
                self.framesLoaded.emit(loaded)
                self.folderLoaded.emit(path, loaded)
                return True

        return False
