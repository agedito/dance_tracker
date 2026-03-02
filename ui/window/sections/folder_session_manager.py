from pathlib import Path
from typing import Callable

from ui.widgets.frame_store import FrameStore
from ui.window.sections.preferences_manager import PreferencesManager


class FolderSessionManager:
    """Single responsibility: load folders and remember frames."""

    def __init__(
            self,
            preferences: PreferencesManager,
            frame_store: FrameStore,
            on_frames_loaded: Callable[[int, int], None],
    ):
        self._prefs = preferences
        self._frame_store = frame_store
        self._on_frames_loaded = on_frames_loaded
        self.current_folder_path: str | None = None

    def load_folder(self, folder_path: str, target_frame: int | None = None):
        frame_count = self._frame_store.load_folder(folder_path)
        if frame_count <= 0:
            return

        normalized = str(Path(folder_path).expanduser())
        self.current_folder_path = normalized

        frame_to_restore = (
            self._prefs.saved_frame_for_folder(normalized)
            if target_frame is None
            else target_frame
        )
        self._on_frames_loaded(frame_count, frame_to_restore)

    def remember_current_frame(self, cur_frame: int):
        self._prefs.remember_frame(self.current_folder_path, cur_frame)

    def on_folder_dropped(self, folder_path: str, cur_frame: int):
        self.remember_current_frame(cur_frame)
        self.current_folder_path = str(Path(folder_path).expanduser())
