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


class _LogEntryStore:
    """Data model for log entries: CRUD and progress-key tracking."""

    def __init__(self, history_limit: int):
        self._history_limit = max(1, history_limit)
        self._entries: list[_LogEntry] = []
        self._by_key: dict[str, int] = {}
        self._next_id = 1

    @property
    def entries(self) -> list[_LogEntry]:
        return self._entries

    def new_id(self) -> int:
        value = self._next_id
        self._next_id += 1
        return value

    def append(self, entry: _LogEntry) -> None:
        self._entries.insert(0, entry)
        self._entries = self._entries[: self._history_limit]
        valid = {e.entry_id for e in self._entries}
        self._by_key = {k: v for k, v in self._by_key.items() if v in valid}

    def register_key(self, key: str, entry_id: int) -> None:
        self._by_key[key] = entry_id

    def unregister_key(self, key: str) -> None:
        self._by_key.pop(key, None)

    def remove(self, entry_id: int) -> _LogEntry | None:
        entry = next((e for e in self._entries if e.entry_id == entry_id), None)
        if entry is None:
            return None
        if entry.progress_key is not None:
            self._by_key.pop(entry.progress_key, None)
        self._entries = [e for e in self._entries if e.entry_id != entry_id]
        return entry

    def find_progress(self, key: str) -> _LogEntry | None:
        nkey = (key or "").strip()
        eid = self._by_key.get(nkey)
        if eid is None:
            return None
        return next((e for e in self._entries if e.entry_id == eid), None)


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
        self._store = _LogEntryStore(history_limit)

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
        entry = _LogEntry(entry_id=self._store.new_id(), text=message, group=group, status=normalized_status)
        self._store.append(entry)
        self._refresh_entries()

    def show_progress(self, key: str, text: str, group: str | None = None):
        normalized_key = (key or "").strip()
        message = (text or "").strip()
        if not normalized_key or not message:
            return

        existing = self._store.find_progress(normalized_key)
        if existing is not None:
            existing.text = message
            existing.group = group
            existing.progress_value = 0
            existing.status = None
            self._refresh_entries()
            return

        entry = _LogEntry(
            entry_id=self._store.new_id(),
            text=message,
            group=group,
            progress_key=normalized_key,
            progress_value=0,
        )
        self._store.register_key(normalized_key, entry.entry_id)
        self._store.append(entry)
        self._refresh_entries()

    def update_progress(self, key: str, value: int, text: str | None = None):
        entry = self._store.find_progress(key)
        if entry is None:
            return
        entry.progress_value = max(0, min(100, int(value)))
        if text is not None and text.strip():
            entry.text = text.strip()
        self._refresh_entries()

    def complete_progress(self, key: str, status: str, text: str | None = None):
        entry = self._store.find_progress(key)
        if entry is None:
            return
        entry.progress_key = None
        entry.progress_value = None
        entry.status = self._normalize_status(status)
        if text is not None and text.strip():
            entry.text = text.strip()
        self._store.unregister_key(key)
        self._refresh_entries()

    def _refresh_entries(self):
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not self._store.entries:
            self.empty_label.show()
            return

        self.empty_label.hide()

        self._content_layout.insertWidget(
            self._content_layout.count() - 1,
            self._build_boundary_widget(self._START_BOUNDARY_TEXT),
        )

        rendered_groups: set[str] = set()
        for entry in self._store.entries:
            if entry.group and entry.group not in rendered_groups:
                rendered_groups.add(entry.group)
                group_label = QLabel(entry.group)
                group_label.setObjectName("LogGroup")
                self._content_layout.insertWidget(self._content_layout.count() - 1, group_label)

            self._content_layout.insertWidget(self._content_layout.count() - 1, self._build_entry_widget(entry))

        self._content_layout.insertWidget(
            self._content_layout.count() - 1,
            self._build_boundary_widget(self._END_BOUNDARY_TEXT),
        )

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
        self._store.remove(entry_id)
        self._refresh_entries()

    def _normalize_status(self, status: str) -> str:
        normalized = (status or "").strip().lower()
        if normalized in self._STATUS_COLORS:
            return normalized
        return "info"
