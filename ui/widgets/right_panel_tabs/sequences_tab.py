from pathlib import Path
from typing import Callable
import shutil

from PySide6.QtCore import QPoint, QEvent, QSize, Qt, QUrl, QMimeData, Signal
from PySide6.QtGui import (
    QDesktopServices,
    QDrag,
    QDragEnterEvent,
    QDropEvent,
    QIcon,
    QMouseEvent,
)
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.interface.media import MediaPort
from app.track_app.sections.video_manager.manager import VIDEO_SUFFIXES
from ui.widgets.drop_handler import DropHandler
from ui.widgets.right_panel_tabs.drag_scroll_area import DragScrollArea
from ui.window.sections.preferences_manager import PreferencesManager


class SequencesTabWidget(QWidget):
    _THUMBNAIL_SIZE = QSize(160, 110)
    _SEQUENCE_MIME_TYPE = "application/x-dance-tracker-sequence"

    def __init__(
            self,
            preferences: PreferencesManager,
            media_manager: MediaPort,
            on_sequence_removed: Callable[[str], None] | None = None,
    ):
        super().__init__()
        self._prefs = preferences
        self._media_manager = media_manager
        self._on_sequence_removed = on_sequence_removed
        self._drop_handler = DropHandler(media_manager, parent=self)
        self._selected_path: str | None = None
        self._folders: list[str] = []

        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._scroll = DragScrollArea()
        self._scroll.setObjectName("ScrollArea")
        self._scroll.setWidgetResizable(True)
        self._scroll.viewport().installEventFilter(self)
        container = QWidget()
        self._grid = QGridLayout(container)
        self._grid.setSpacing(10)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._scroll.setWidget(container)
        layout.addWidget(self._scroll, 1)

        self.refresh()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat(self._SEQUENCE_MIME_TYPE):
            event.acceptProposedAction()
            return

        if self._drop_handler.can_accept(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasFormat(self._SEQUENCE_MIME_TYPE):
            event.acceptProposedAction()
            return

        if self._drop_handler.handle_drop(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def refresh(self):
        self._folders = self._prefs.recent_folders()
        if self._selected_path not in self._folders:
            self._selected_path = None
        self._rebuild_grid()

    def eventFilter(self, watched: QWidget, event: QEvent) -> bool:
        if watched is self._scroll.viewport() and event.type() == QEvent.Type.Resize:
            self._rebuild_grid()
        return super().eventFilter(watched, event)

    def _rebuild_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not self._folders:
            empty = QLabel("There are no recent sequences yet.")
            empty.setObjectName("Muted")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid.addWidget(empty, 0, 0)
            return

        available_width = max(1, self._scroll.viewport().width())
        cell_width = self._THUMBNAIL_SIZE.width() + self._grid.horizontalSpacing()
        columns = max(1, available_width // cell_width)

        for idx, folder in enumerate(self._folders):
            row, col = divmod(idx, columns)
            self._grid.addWidget(self._sequence_button(folder), row, col)

    def _sequence_button(self, folder_path: str) -> QPushButton:
        button = _SequenceThumbnailButton(
            folder_path=folder_path,
            size=self._THUMBNAIL_SIZE,
            sequence_mime_type=self._SEQUENCE_MIME_TYPE,
        )
        button.folderDropped.connect(self._move_folder_relative)
        button.setObjectName("SequenceThumbnail")
        button.setProperty("isSelected", folder_path == self._selected_path)
        button.style().unpolish(button)
        button.style().polish(button)
        button.setToolTip(folder_path)
        button.clicked.connect(lambda _=False, selected_path=folder_path: self._select_and_load(selected_path))
        button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        button.customContextMenuRequested.connect(
            lambda pos, origin=button, selected_path=folder_path: self._show_sequence_menu(origin, selected_path, pos)
        )

        thumbnail = self._prefs.thumbnail_for_folder(folder_path)
        if thumbnail:
            button.setIcon(QIcon(thumbnail))
            button.setIconSize(QSize(146, 82))
        return button

    def _move_folder_relative(self, dragged_folder: str, target_folder: str, drop_after: bool):
        if dragged_folder == target_folder:
            return
        if dragged_folder not in self._folders or target_folder not in self._folders:
            return

        updated = [folder for folder in self._folders if folder != dragged_folder]
        target_idx = updated.index(target_folder)
        if drop_after:
            target_idx += 1
        updated.insert(target_idx, dragged_folder)

        self._folders = updated
        self._prefs.save_recent_folders_order(updated)
        self._rebuild_grid()

    def _show_sequence_menu(self, origin: QWidget, folder_path: str, pos: QPoint):
        menu = QMenu(self)
        open_folder_action = menu.addAction("Open Folder")
        remove_action = menu.addAction("Remove")
        delete_video_and_frames_action = menu.addAction("Delete Video and Frames")

        selected_action = menu.exec(origin.mapToGlobal(pos))
        if selected_action is open_folder_action:
            self._open_folder(folder_path)
            return
        if selected_action is remove_action:
            self._remove_sequence(folder_path)
            return
        if selected_action is delete_video_and_frames_action:
            self._delete_video_and_frames(folder_path)

    def _open_folder(self, folder_path: str):
        folder = Path(folder_path).expanduser()
        target = folder if folder.exists() else folder.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def _delete_video_and_frames(self, folder_path: str):
        folder = Path(folder_path).expanduser()
        video_file = self._find_video_for_frames(folder)

        if folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)

        if folder.name == "frames":
            frames_mino = folder.parent / "frames_mino"
            if frames_mino.is_dir():
                shutil.rmtree(frames_mino, ignore_errors=True)

        if video_file and video_file.exists():
            video_file.unlink(missing_ok=True)

        self._remove_sequence(folder_path)

    @staticmethod
    def _find_video_for_frames(folder: Path) -> Path | None:
        parent = folder.parent
        if not parent.is_dir():
            return None

        videos = [
            file
            for file in sorted(parent.iterdir())
            if file.is_file() and file.suffix.lower() in VIDEO_SUFFIXES
        ]
        return videos[0] if videos else None

    def _remove_sequence(self, folder_path: str):
        self._prefs.remove_recent_folder(folder_path)
        if self._selected_path == folder_path:
            self._selected_path = None
        if self._on_sequence_removed:
            self._on_sequence_removed(folder_path)
        self.refresh()

    def _select_and_load(self, folder_path: str):
        self._selected_path = folder_path
        self._media_manager.load(folder_path)
        self._rebuild_grid()


class _SequenceThumbnailButton(QPushButton):
    folderDropped = Signal(str, str, bool)

    def __init__(self, folder_path: str, size: QSize, sequence_mime_type: str):
        super().__init__("")
        self._folder_path = folder_path
        self._sequence_mime_type = sequence_mime_type
        self._drag_start_pos: QPoint | None = None
        self.setAcceptDrops(True)
        self.setFixedSize(size)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_start_pos is None:
            return

        distance = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
        if distance < 8:
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData(self._sequence_mime_type, self._folder_path.encode("utf-8"))
        drag.setMimeData(mime_data)
        drag.setPixmap(self.grab())
        drag.setHotSpot(event.position().toPoint())
        drag.exec(Qt.DropAction.MoveAction)
        self._drag_start_pos = None

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat(self._sequence_mime_type):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if not event.mimeData().hasFormat(self._sequence_mime_type):
            event.ignore()
            return

        dragged = bytes(event.mimeData().data(self._sequence_mime_type)).decode("utf-8")
        drop_after = event.position().x() >= self.width() / 2
        self.folderDropped.emit(dragged, self._folder_path, drop_after)
        event.acceptProposedAction()
