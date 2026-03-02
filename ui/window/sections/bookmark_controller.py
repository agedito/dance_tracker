from typing import Callable

from app.interface.sequence_data import SequenceDataPort
from ui.window.sections.folder_session_manager import FolderSessionManager


class BookmarkController:
    """Dispatches bookmark mutations to the App port and keeps the timeline in sync."""

    def __init__(
        self,
        sequence_data: SequenceDataPort,
        folder_session: FolderSessionManager,
        get_total_frames: Callable[[], int],
        get_cur_frame: Callable[[], int],
        on_bookmarks_refreshed: Callable,
        on_go_to_frame: Callable[[int], None],
    ):
        self._sequence_data = sequence_data
        self._folder_session = folder_session
        self._get_total_frames = get_total_frames
        self._get_cur_frame = get_cur_frame
        self._on_bookmarks_refreshed = on_bookmarks_refreshed
        self._on_go_to_frame = on_go_to_frame

    def refresh(self) -> None:
        folder_path = self._folder_path()
        if not folder_path:
            self._on_bookmarks_refreshed([])
            return
        total = self._get_total_frames()
        bookmarks = self._sequence_data.read_bookmarks(folder_path)
        valid = [b for b in bookmarks if 0 <= b.frame < total]
        self._on_bookmarks_refreshed(valid)

    def request_add(self, frame: int) -> None:
        folder_path = self._folder_path()
        if folder_path:
            self._sequence_data.add_bookmark(folder_path, self._clamp(frame))

    def request_move(self, source_frame: int, target_frame: int) -> None:
        folder_path = self._folder_path()
        if folder_path:
            self._sequence_data.move_bookmark(folder_path, source_frame, self._clamp(target_frame))

    def request_remove(self, frame: int) -> None:
        folder_path = self._folder_path()
        if folder_path:
            self._sequence_data.remove_bookmark(folder_path, frame)

    def request_name_change(self, frame: int, name: str) -> None:
        folder_path = self._folder_path()
        if folder_path:
            self._sequence_data.set_bookmark_name(folder_path, frame, name)

    def request_lock_change(self, frame: int, locked: bool) -> None:
        folder_path = self._folder_path()
        if folder_path:
            self._sequence_data.set_bookmark_locked(folder_path, frame, locked)

    def go_to_previous(self) -> None:
        folder_path = self._folder_path()
        if not folder_path:
            return
        frame = self._sequence_data.previous_bookmark_frame(folder_path, self._get_cur_frame())
        if frame is not None:
            self._on_go_to_frame(frame)

    def go_to_next(self) -> None:
        folder_path = self._folder_path()
        if not folder_path:
            return
        frame = self._sequence_data.next_bookmark_frame(folder_path, self._get_cur_frame())
        if frame is not None:
            self._on_go_to_frame(frame)

    def _folder_path(self) -> str | None:
        return self._folder_session.current_folder_path

    def _clamp(self, frame: int) -> int:
        return max(0, min(frame, self._get_total_frames() - 1))
