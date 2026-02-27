from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.interface.media import MediaPort
from ui.widgets.drop_handler import DropHandler
from ui.widgets.right_panel_tabs.drag_scroll_area import DragScrollArea
from ui.window.sections.preferences_manager import PreferencesManager


class SequencesTabWidget(QWidget):
    _THUMBNAIL_SIZE = QSize(160, 110)

    def __init__(self, preferences: PreferencesManager, media_manager: MediaPort):
        super().__init__()
        self._prefs = preferences
        self._media_manager = media_manager
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
        if self._drop_handler.can_accept(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if self._drop_handler.handle_drop(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def refresh(self):
        self._folders = list(reversed(self._prefs.recent_folders()))
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
            empty = QLabel("Aún no hay secuencias recientes.")
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
        path = Path(folder_path).expanduser()
        button = QPushButton("")
        button.setObjectName("SequenceThumbnail")
        button.setProperty("isSelected", folder_path == self._selected_path)
        button.style().unpolish(button)
        button.style().polish(button)
        button.setToolTip(folder_path)
        button.setFixedSize(self._THUMBNAIL_SIZE)
        button.clicked.connect(lambda _=False, selected_path=folder_path: self._select_and_load(selected_path))

        thumbnail = self._prefs.thumbnail_for_folder(folder_path)
        if thumbnail:
            button.setIcon(QIcon(thumbnail))
            button.setIconSize(QSize(146, 82))
        return button

    def _select_and_load(self, folder_path: str):
        self._selected_path = folder_path
        self._media_manager.load(folder_path)
        self._rebuild_grid()
