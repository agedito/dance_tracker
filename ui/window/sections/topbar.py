from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

from app.interface.sequence_data import SequenceDataPort


class _EditableTitleLabel(QLabel):
    doubleClicked = Signal()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class TopBar(QWidget):
    """Render top bar and current sequence title with inline rename support."""

    def __init__(self, on_close, sequence_data: SequenceDataPort):
        super().__init__()

        self.setObjectName("TopBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        title = QLabel("MAIN VIEWER")
        title.setObjectName("TopTitle")
        layout.addWidget(title)

        self._sequence_data = sequence_data
        self._active_folder: str | None = None
        self._sequence_name = _EditableTitleLabel("No sequence selected")
        self._sequence_name.setObjectName("TopSequenceName")
        self._sequence_name.setCursor(Qt.CursorShape.IBeamCursor)
        self._sequence_name.doubleClicked.connect(self._start_rename)
        layout.addSpacing(12)
        layout.addWidget(self._sequence_name)

        self._sequence_editor = QLineEdit()
        self._sequence_editor.setObjectName("TopSequenceEditor")
        self._sequence_editor.setPlaceholderText("Sequence name")
        self._sequence_editor.hide()
        self._sequence_editor.editingFinished.connect(self._finish_rename)
        layout.addWidget(self._sequence_editor)

        layout.addStretch(1)

        close_button = QPushButton("✕")
        close_button.setObjectName("TopCloseButton")
        close_button.setToolTip("Close app")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_button.clicked.connect(on_close)
        layout.addSpacing(10)
        layout.addWidget(close_button)

    def refresh_icons(self):
        """Compatibility no-op: top bar no longer shows recent media."""

    def set_active_folder(self, folder_path):
        if not folder_path:
            self._active_folder = None
            self._sequence_name.setText("No sequence selected")
            self._sequence_name.show()
            self._sequence_editor.hide()
            return

        self._active_folder = folder_path
        name = self._sequence_data.get_sequence_name(folder_path)
        if not name:
            name = Path(folder_path).expanduser().parent.name or "Sequence"
        self._sequence_name.setText(name)

    def _start_rename(self):
        if self._active_folder is None:
            return

        self._sequence_editor.setText(self._sequence_name.text())
        self._sequence_name.hide()
        self._sequence_editor.show()
        self._sequence_editor.setFocus()
        self._sequence_editor.selectAll()

    def _finish_rename(self):
        if self._active_folder is None:
            self._sequence_editor.hide()
            self._sequence_name.show()
            return

        new_name = self._sequence_editor.text().strip()
        if not new_name:
            self._sequence_editor.setText(self._sequence_name.text())
        else:
            self._sequence_data.set_sequence_name(self._active_folder, new_name)
            self._sequence_name.setText(new_name)

        self._sequence_editor.hide()
        self._sequence_name.show()
