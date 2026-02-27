import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget


class _EditableTitleLabel(QLabel):
    doubleClicked = Signal()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class TopBar(QWidget):
    """Render top bar and current sequence title with inline rename support."""

    def __init__(self, on_close):
        super().__init__()

        self.setObjectName("TopBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        title = QLabel("MAIN VIEWER")
        title.setObjectName("TopTitle")
        layout.addWidget(title)

        self._active_folder: Path | None = None
        self._active_metadata_path: Path | None = None
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
            self._active_metadata_path = None
            self._sequence_name.setText("No sequence selected")
            self._sequence_name.show()
            self._sequence_editor.hide()
            return

        self._active_folder = Path(folder_path).expanduser().resolve()
        self._active_metadata_path = self._find_metadata_path(self._active_folder)
        self._sequence_name.setText(self._load_sequence_name())

    def _start_rename(self):
        if self._active_metadata_path is None:
            return

        self._sequence_editor.setText(self._sequence_name.text())
        self._sequence_name.hide()
        self._sequence_editor.show()
        self._sequence_editor.setFocus()
        self._sequence_editor.selectAll()

    def _finish_rename(self):
        if self._active_metadata_path is None:
            self._sequence_editor.hide()
            self._sequence_name.show()
            return

        new_name = self._sequence_editor.text().strip()
        if not new_name:
            self._sequence_editor.setText(self._sequence_name.text())
        else:
            self._save_sequence_name(new_name)
            self._sequence_name.setText(new_name)

        self._sequence_editor.hide()
        self._sequence_name.show()

    def _load_sequence_name(self) -> str:
        default_name = self._active_folder.parent.name if self._active_folder else "Sequence"
        if self._active_metadata_path is None:
            return default_name

        payload = self._read_json(self._active_metadata_path)
        if payload is None:
            return default_name

        sequence = payload.get("sequence")
        if not isinstance(sequence, dict):
            return default_name

        value = sequence.get("name")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return default_name

    def _save_sequence_name(self, sequence_name: str):
        if self._active_metadata_path is None:
            return

        payload = self._read_json(self._active_metadata_path)
        if payload is None:
            return

        sequence = payload.get("sequence")
        if not isinstance(sequence, dict):
            sequence = {}
            payload["sequence"] = sequence

        sequence["name"] = sequence_name

        self._active_metadata_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _read_json(path: Path) -> dict | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _resolve_metadata_path(value: str, root: Path) -> Path:
        candidate = Path(value).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
        return (root / candidate).resolve()

    @classmethod
    def _find_metadata_path(cls, folder: Path) -> Path | None:
        if not folder.exists():
            return None

        for metadata_path in folder.parent.glob("*.json"):
            payload = cls._read_json(metadata_path)
            if payload is None:
                continue

            frames_value = payload.get("frames") or payload.get("frames_path")
            if not isinstance(frames_value, str):
                continue

            resolved_frames = cls._resolve_metadata_path(frames_value, metadata_path.parent)
            if resolved_frames == folder:
                return metadata_path
        return None
