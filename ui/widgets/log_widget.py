from collections import deque

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QLabel, QListWidget, QVBoxLayout


class LogWidget(QFrame):
    _EMPTY_TEXT = "No logs"

    def __init__(self, display_ms: int, history_limit: int, parent=None):
        super().__init__(parent)
        self.display_ms = max(100, int(display_ms))
        self.history_limit = max(1, int(history_limit))
        self._history = deque(maxlen=self.history_limit)
        self._current_message = ""

        self.setObjectName("LogWidget")

        container = QVBoxLayout(self)
        container.setContentsMargins(0, 0, 0, 0)
        container.setSpacing(8)

        self.current_label = QLabel(self._EMPTY_TEXT)
        self.current_label.setObjectName("LogCurrent")
        self.current_label.setWordWrap(True)
        current_font = self.current_label.font()
        current_font.setPointSize(current_font.pointSize() + 2)
        self.current_label.setFont(current_font)
        container.addWidget(self.current_label)

        self.history_list = QListWidget()
        self.history_list.setObjectName("LogHistoryList")
        self.history_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.history_list.setWordWrap(True)
        self.history_list.setSpacing(2)
        container.addWidget(self.history_list)

        self._clear_timer = QTimer(self)
        self._clear_timer.setSingleShot(True)
        self._clear_timer.timeout.connect(self._clear_current)

    def log(self, text: str):
        message = (text or "").strip()
        if not message:
            return

        self._archive_current_message()
        self._current_message = message
        self.current_label.setText(message)
        self._clear_timer.start(self.display_ms)

    def _clear_current(self):
        self._archive_current_message()
        self.current_label.setText(self._EMPTY_TEXT)

    def _archive_current_message(self):
        if not self._current_message:
            return

        self._history.appendleft(self._current_message)
        self._current_message = ""
        self._refresh_history()

    def _refresh_history(self):
        self.history_list.clear()
        for message in self._history:
            self.history_list.addItem(message)
