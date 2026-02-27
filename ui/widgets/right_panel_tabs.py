from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.interface.media import MediaPort
from app.interface.music import SongMetadata
from ui.widgets.drop_handler import DropHandler
from ui.widgets.thumbnail import ThumbnailWidget
from ui.window.sections.preferences_manager import PreferencesManager


class DragScrollArea(QScrollArea):
    """Scroll area that supports click-and-drag scrolling and hides scrollbars."""

    def __init__(self):
        super().__init__()
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._dragging = False
        self._last_pos = None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._last_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging and self._last_pos is not None:
            delta = event.position() - self._last_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            self._last_pos = event.position()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self._last_pos = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)


def section_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("SectionTitle")
    return label


class LayerViewersTabWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(section_label("LAYER VIEWERS"))
        grid1 = QGridLayout()
        grid1.setSpacing(8)
        grid1.addWidget(self._thumb("Layer 1: Color Grade", 10), 0, 0)
        grid1.addWidget(self._thumb("Layer 1: Output", 17), 0, 1)
        layout.addLayout(grid1)

        layout.addWidget(section_label("LAYER 2: OBJECT MASK"))
        grid2 = QGridLayout()
        grid2.setSpacing(8)
        grid2.addWidget(self._thumb("Layer 2: Mask", 24), 0, 0)
        grid2.addWidget(self._thumb("Layer 2: Overlay", 31), 0, 1)
        layout.addLayout(grid2)

        footer = QLabel("Mock: thumbnails procedural + poses YOLO 3D.")
        footer.setObjectName("FooterNote")
        layout.addWidget(footer)
        layout.addStretch(1)

    @staticmethod
    def _thumb(label: str, seed: int) -> QFrame:
        frame = QFrame()
        frame.setObjectName("ThumbFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(ThumbnailWidget(label, seed))
        return frame


class MusicTabWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(section_label("Music"))

        self._status_value = QLabel("not_run")
        self._title_value = QLabel("—")
        self._artist_value = QLabel("—")
        self._album_value = QLabel("—")
        self._provider_value = QLabel("—")
        self._message_value = QLabel("")
        self._message_value.setWordWrap(True)

        for label, value in (
            ("Estado", self._status_value),
            ("Título", self._title_value),
            ("Artista", self._artist_value),
            ("Álbum", self._album_value),
            ("Proveedor", self._provider_value),
        ):
            layout.addWidget(QLabel(f"{label}:"))
            layout.addWidget(value)

        layout.addWidget(self._message_value)
        layout.addStretch(1)

    def update_song_info(self, song: SongMetadata):
        self._status_value.setText(song.status)
        self._title_value.setText(song.title or "—")
        self._artist_value.setText(song.artist or "—")
        self._album_value.setText(song.album or "—")
        self._provider_value.setText(song.provider or "—")
        self._message_value.setText(song.message or "")


class EmbedingsTabWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section_label("Embedings"))

        info = QLabel("Sección reservada para futuras visualizaciones de embeddings.")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch(1)


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
