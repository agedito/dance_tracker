from pathlib import Path
from typing import Callable

from app.track_app.frame_state.frame_store import FrameStore
from ui.window.sections.preferences_manager import PreferencesManager


class FolderSessionManager:
    """Single responsibility: load folders, track current folder, remember/restore frames."""

    def __init__(
            self,
            preferences: PreferencesManager,
            frame_store: FrameStore,
            on_frames_loaded: Callable[[int, int], None],
            on_icons_changed: Callable[[], None],
    ):
        self._prefs = preferences
        self._frame_store = frame_store
        self._on_frames_loaded = on_frames_loaded
        self._on_icons_changed = on_icons_changed
        self.current_folder_path: str | None = None

    def load_folder(self, folder_path: str, target_frame: int | None = None):
        self.remember_current_frame(0)  # save before switching
        frame_count = self._frame_store.load_folder(folder_path)
        if frame_count <= 0:
            return

        normalized = str(Path(folder_path).expanduser())
        self.current_folder_path = normalized
        self._prefs.register_recent_folder(folder_path)
        self._on_icons_changed()

        frame_to_restore = (
            self._prefs.saved_frame_for_folder(normalized)
            if target_frame is None
            else target_frame
        )
        self._on_frames_loaded(frame_count, frame_to_restore)

    def remember_current_frame(self, cur_frame: int):
        self._prefs.remember_frame(self.current_folder_path, cur_frame)

    def restore_last_session(self) -> int | None:
        """Try to restore the last session. Returns target frame or None if nothing to restore."""
        last_folder = self._prefs.last_opened_folder()
        if not last_folder:
            recent = self._prefs.recent_folders()
            last_folder = recent[0] if recent else None

        if last_folder:
            target = self._prefs.saved_frame_for_folder(last_folder)
            self.load_folder(last_folder, target_frame=target)
            return target
        return None

    def on_folder_dropped(self, folder_path: str, cur_frame: int):
        """Handle a folder drag-dropped onto the viewer."""
        self.remember_current_frame(cur_frame)
        normalized = str(Path(folder_path).expanduser())
        self.current_folder_path = normalized
        self._prefs.register_recent_folder(folder_path)
        self._on_icons_changed()
