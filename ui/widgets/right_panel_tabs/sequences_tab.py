from pathlib import Path

from PySide6.QtCore import QPoint, QEvent, QSize, Qt, QUrl, QMimeData, Signal
from PySide6.QtGui import QDesktopServices, QDrag, QDragEnterEvent, QDropEvent, QIcon, QMouseEvent
from PySide6.QtWidgets import QGridLayout, QLabel, QMenu, QPushButton, QVBoxLayout, QWidget

from app.interface.event_bus import Event, EventBus
from app.interface.sequences import SequencePort, SequenceState
from ui.widgets.drop_handler import DropHandler
from ui.widgets.right_panel_tabs.drag_scroll_area import DragScrollArea


class SequencesTabWidget(QWidget):
    _THUMBNAIL_SIZE = QSize(160, 110)
    _SEQUENCE_MIME_TYPE = "application/x-dance-tracker-sequence"

    def __init__(self, media_manager, sequences: SequencePort, event_bus: EventBus):
        super().__init__()
        self._sequences = sequences
        self._drop_handler = DropHandler(media_manager, parent=self)
        self._state = SequenceState(items=[], active_folder=None)

        self.setAcceptDrops(True)
        event_bus.on(Event.SequencesChanged, self._on_sequences_changed)

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

        self._sequences.refresh()

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

    def eventFilter(self, watched: QWidget, event: QEvent) -> bool:
        if watched is self._scroll.viewport() and event.type() == QEvent.Type.Resize:
            self._rebuild_grid()
        return super().eventFilter(watched, event)

    def _on_sequences_changed(self, state: SequenceState) -> None:
        self._state = state
        self._rebuild_grid()

    def _rebuild_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not self._state.items:
            empty = QLabel("There are no recent sequences yet.")
            empty.setObjectName("Muted")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid.addWidget(empty, 0, 0)
            return

        available_width = max(1, self._scroll.viewport().width())
        cell_width = self._THUMBNAIL_SIZE.width() + self._grid.horizontalSpacing()
        columns = max(1, available_width // cell_width)

        for idx, item in enumerate(self._state.items):
            row, col = divmod(idx, columns)
            self._grid.addWidget(self._sequence_button(item.folder_path, item.thumbnail_path), row, col)

    def _sequence_button(self, folder_path: str, thumbnail_path: str | None) -> QPushButton:
        button = _SequenceThumbnailButton(
            folder_path=folder_path,
            size=self._THUMBNAIL_SIZE,
            sequence_mime_type=self._SEQUENCE_MIME_TYPE,
        )
        button.folderDropped.connect(self._sequences.move)
        button.setObjectName("SequenceThumbnail")
        button.setProperty("isSelected", folder_path == self._state.active_folder)
        button.style().unpolish(button)
        button.style().polish(button)
        button.setToolTip(folder_path)
        button.clicked.connect(lambda _=False, selected_path=folder_path: self._sequences.load(selected_path))
        button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        button.customContextMenuRequested.connect(
            lambda pos, origin=button, selected_path=folder_path: self._show_sequence_menu(origin, selected_path, pos)
        )

        if thumbnail_path:
            button.setIcon(QIcon(thumbnail_path))
            button.setIconSize(QSize(146, 82))
        return button

    def _show_sequence_menu(self, origin: QWidget, folder_path: str, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #1A1F23;
                border: 1px solid #2B343B;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3A3F45;
            }
            QMenu::separator {
                height: 1px;
                background: #4B525A;
                margin: 6px 4px;
            }
            """
        )
        open_folder_action = menu.addAction("Open Folder")
        remove_action = menu.addAction("Remove")
        menu.addSeparator()
        delete_video_and_frames_action = menu.addAction("Delete Video and Frames")

        selected_action = menu.exec(origin.mapToGlobal(pos))
        if selected_action is open_folder_action:
            self._open_folder(folder_path)
            return
        if selected_action is remove_action:
            self._sequences.remove(folder_path)
            return
        if selected_action is delete_video_and_frames_action:
            self._sequences.delete_video_and_frames(folder_path)

    @staticmethod
    def _open_folder(folder_path: str):
        folder = Path(folder_path).expanduser()
        target = folder if folder.exists() else folder.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))


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
