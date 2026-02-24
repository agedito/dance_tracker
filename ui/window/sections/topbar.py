from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QPushButton, QWidget

from ui.window.sections.preferences_manager import PreferencesManager


class TopBar(QWidget):
    """Single responsibility: render the top bar with recent folder icons."""

    def __init__(
            self,
            preferences: PreferencesManager,
            on_folder_clicked: Callable[[str], None],
            on_close: Callable[[], None],
    ):
        super().__init__()
        self._prefs = preferences
        self._on_folder_clicked = on_folder_clicked

        self.setObjectName("TopBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        title = QLabel("MAIN VIEWER")
        title.setObjectName("TopTitle")
        layout.addWidget(title)

        hint = QLabel("Drop folder or video to load frames")
        hint.setObjectName("TopHint")

        # Recent folders container
        self._folders_container = QWidget()
        self._folders_layout = QHBoxLayout(self._folders_container)
        self._folders_layout.setContentsMargins(0, 0, 0, 0)
        self._folders_layout.setSpacing(6)

        layout.addSpacing(12)
        layout.addWidget(self._folders_container)
        layout.addStretch(1)
        layout.addWidget(hint)

        close_button = QPushButton("✕")
        close_button.setObjectName("TopCloseButton")
        close_button.setToolTip("Close app")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(on_close)
        layout.addSpacing(10)
        layout.addWidget(close_button)

        self.refresh_icons()

    def refresh_icons(self):
        """Rebuild folder icon buttons from current preferences."""
        while self._folders_layout.count():
            item = self._folders_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        for folder in self._prefs.recent_folders():
            folder_name = Path(folder).name or Path(folder).anchor or folder
            btn = QPushButton(folder_name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setObjectName("RecentFolderIcon")
            btn.setToolTip(folder)

            thumbnail = self._prefs.thumbnail_for_folder(folder)
            if thumbnail:
                btn.setIcon(QIcon(thumbnail))
                btn.setIconSize(QSize(42, 42))

            btn.clicked.connect(lambda _=False, p=folder: self._on_folder_clicked(p))

            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, p=folder, b=btn: self._show_context_menu(p, b.mapToGlobal(pos))
            )
            self._folders_layout.addWidget(btn)

    def _show_context_menu(self, folder_path: str, global_pos):
        menu = QMenu(self)
        remove = QAction("Remove folder", self)
        remove.triggered.connect(lambda _=False, p=folder_path: self._remove_folder(p))
        menu.addAction(remove)
        menu.exec(global_pos)

    def _remove_folder(self, folder_path: str):
        self._prefs.remove_recent_folder(folder_path)
        self.refresh_icons()
