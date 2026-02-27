from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.interface.media import MediaPort
from ui.widgets.drop_handler import DropHandler
from ui.widgets.right_panel_tabs.drag_scroll_area import DragScrollArea
from ui.window.sections.preferences_manager import PreferencesManager


class SequencesTabWidget(QWidget):
    def __init__(self, preferences: PreferencesManager, media_manager: MediaPort):
        super().__init__()
        self._prefs = preferences
        self._media_manager = media_manager
        self._drop_handler = DropHandler(media_manager, parent=self)

        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        hint = QLabel("Arrastra videos o carpetas aquí")
        hint.setObjectName("Muted")
        layout.addWidget(hint)

        self._scroll = DragScrollArea()
        self._scroll.setObjectName("ScrollArea")
        self._scroll.setWidgetResizable(True)
        container = QWidget()
        self._grid = QGridLayout(container)
        self._grid.setSpacing(10)
        self._grid.setContentsMargins(0, 0, 0, 0)
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
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        folders = list(reversed(self._prefs.recent_folders()))
        for idx, folder in enumerate(folders):
            row, col = divmod(idx, 2)
            self._grid.addWidget(self._sequence_button(folder), row, col)

        if not folders:
            empty = QLabel("Aún no hay secuencias recientes.")
            empty.setObjectName("Muted")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid.addWidget(empty, 0, 0, 1, 2)

    def _sequence_button(self, folder_path: str) -> QPushButton:
        path = Path(folder_path).expanduser()
        button = QPushButton(path.name)
        button.setToolTip(folder_path)
        button.setFixedSize(QSize(160, 110))
        button.clicked.connect(lambda _=False, selected_path=folder_path: self._media_manager.load(selected_path))

        thumbnail = self._prefs.thumbnail_for_folder(folder_path)
        if thumbnail:
            button.setIcon(QIcon(thumbnail))
            button.setIconSize(QSize(146, 82))
        return button
