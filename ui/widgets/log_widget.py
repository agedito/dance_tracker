from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.right_panel_tabs.drag_scroll_area import DragScrollArea


@dataclass
class _LogEntry:
    entry_id: int
    text: str
    group: str | None = None
    status: str | None = None
    progress_key: str | None = None
    progress_value: int | None = None


class LogWidget(QFrame):
    _EMPTY_TEXT = "No logs"
    _START_BOUNDARY_TEXT = "Beginning of logs"
    _END_BOUNDARY_TEXT = "End of logs"
    _STATUS_COLORS = {
        "success": "#2ecc71",
        "error": "#e74c3c",
        "warning": "#f1c40f",
        "info": "#8a8a8a",
    }

    def __init__(self, display_ms: int, history_limit: int, parent=None):
        super().__init__(parent)
        self.display_ms = max(100, int(display_ms))
        self.history_limit = max(1, int(history_limit))
        self._entries: list[_LogEntry] = []
        self._entry_by_progress_key: dict[str, int] = {}
        self._next_entry_id = 1

        self.setObjectName("LogWidget")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.empty_label = QLabel(self._EMPTY_TEXT)
        self.empty_label.setObjectName("LogEmpty")
        self.empty_label.setWordWrap(True)
        root.addWidget(self.empty_label)

        self.scroll_area = DragScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(4)
        self._content_layout.addStretch(1)

        self.scroll_area.setWidget(self._content)
        root.addWidget(self.scroll_area)

    def log(self, text: str, group: str | None = None):
        self.log_status(text=text, status="info", group=group)

    def log_status(self, text: str, status: str, group: str | None = None):
        message = (text or "").strip()
        if not message:
            return
        normalized_status = self._normalize_status(status)
        self._append_entry(_LogEntry(entry_id=self._new_entry_id(), text=message, group=group, status=normalized_status))

    def show_progress(self, key: str, text: str, group: str | None = None):
        normalized_key = (key or "").strip()
        message = (text or "").strip()
        if not normalized_key or not message:
            return

        existing_entry = self._find_progress_entry(normalized_key)
        if existing_entry is not None:
            existing_entry.text = message
            existing_entry.group = group
            existing_entry.progress_value = 0
            existing_entry.status = None
            self._refresh_entries()
            return

        entry = _LogEntry(
            entry_id=self._new_entry_id(),
            text=message,
            group=group,
            progress_key=normalized_key,
            progress_value=0,
        )
        self._entry_by_progress_key[normalized_key] = entry.entry_id
        self._append_entry(entry)

    def update_progress(self, key: str, value: int, text: str | None = None):
        entry = self._find_progress_entry(key)
        if entry is None:
            return

        entry.progress_value = max(0, min(100, int(value)))
        if text is not None and text.strip():
            entry.text = text.strip()
        self._refresh_entries()

    def complete_progress(self, key: str, status: str, text: str | None = None):
        entry = self._find_progress_entry(key)
        if entry is None:
            return

        entry.progress_key = None
        entry.progress_value = None
        entry.status = self._normalize_status(status)
        if text is not None and text.strip():
            entry.text = text.strip()

        normalized_key = (key or "").strip()
        self._entry_by_progress_key.pop(normalized_key, None)
        self._refresh_entries()

    def _append_entry(self, entry: _LogEntry):
        self._entries.insert(0, entry)
        self._entries = self._entries[: self.history_limit]
        valid_ids = {item.entry_id for item in self._entries}
        self._entry_by_progress_key = {
            key: entry_id for key, entry_id in self._entry_by_progress_key.items() if entry_id in valid_ids
        }
        self._refresh_entries()

    def _refresh_entries(self):
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not self._entries:
            self.empty_label.show()
            return

        self.empty_label.hide()

        self._content_layout.insertWidget(self._content_layout.count() - 1, self._build_boundary_widget(self._START_BOUNDARY_TEXT))

        rendered_groups: set[str] = set()
        for entry in self._entries:
            if entry.group and entry.group not in rendered_groups:
                rendered_groups.add(entry.group)
                group_label = QLabel(entry.group)
                group_label.setObjectName("LogGroup")
                self._content_layout.insertWidget(self._content_layout.count() - 1, group_label)

            self._content_layout.insertWidget(self._content_layout.count() - 1, self._build_entry_widget(entry))

        self._content_layout.insertWidget(self._content_layout.count() - 1, self._build_boundary_widget(self._END_BOUNDARY_TEXT))

    def _build_entry_widget(self, entry: _LogEntry) -> QWidget:
        card = QFrame()
        card.setObjectName("LogEntryCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(6)

        if entry.status is not None:
            status_dot = QLabel("●")
            status_dot.setObjectName("LogStatusDot")
            status_dot.setStyleSheet(f"color: {self._STATUS_COLORS[entry.status]};")
            header.addWidget(status_dot)

        text_label = QLabel(entry.text)
        text_label.setWordWrap(True)
        text_label.setObjectName("LogEntryText")
        header.addWidget(text_label, 1)

        close_button = QPushButton("×")
        close_button.setObjectName("LogCloseButton")
        close_button.setFixedSize(16, 16)
        close_button.setStyleSheet(
            "QPushButton#LogCloseButton {"
            "padding: 0px;"
            "font-size: 10px;"
            "font-weight: 700;"
            "border-radius: 8px;"
            "min-width: 16px;"
            "max-width: 16px;"
            "min-height: 16px;"
            "max-height: 16px;"
            "}"
        )
        close_button.clicked.connect(lambda: self._remove_entry(entry.entry_id))
        header.addWidget(close_button, 0, Qt.AlignmentFlag.AlignTop)

        layout.addLayout(header)

        if entry.progress_value is not None:
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(entry.progress_value)
            progress.setObjectName("LogEntryProgress")
            layout.addWidget(progress)

        return card

    def _build_boundary_widget(self, text: str) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(2)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setStyleSheet("color: #56616a;")
        layout.addWidget(line)

        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #8f9aa3; font-size: 10px;")
        layout.addWidget(label)

        return container

    def _remove_entry(self, entry_id: int):
        entry = next((item for item in self._entries if item.entry_id == entry_id), None)
        if entry is None:
            return
        if entry.progress_key is not None:
            self._entry_by_progress_key.pop(entry.progress_key, None)
        self._entries = [item for item in self._entries if item.entry_id != entry_id]
        self._refresh_entries()

    def _find_progress_entry(self, key: str) -> _LogEntry | None:
        normalized_key = (key or "").strip()
        entry_id = self._entry_by_progress_key.get(normalized_key)
        if entry_id is None:
            return None
        return next((entry for entry in self._entries if entry.entry_id == entry_id), None)

    def _new_entry_id(self) -> int:
        value = self._next_entry_id
        self._next_entry_id += 1
        return value

    def _normalize_status(self, status: str) -> str:
        normalized = (status or "").strip().lower()
        if normalized in self._STATUS_COLORS:
            return normalized
        return "info"
