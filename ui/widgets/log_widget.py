from collections import deque

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QToolButton, QVBoxLayout


class LogWidget(QFrame):
    def __init__(self, display_ms: int, history_limit: int, parent=None):
        super().__init__(parent)
        self.display_ms = max(100, int(display_ms))
        self.history_limit = max(1, int(history_limit))
        self._history = deque(maxlen=self.history_limit)

        self.setObjectName("LogWidget")

        container = QVBoxLayout(self)
        container.setContentsMargins(0, 0, 0, 0)
        container.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self.current_label = QLabel("Sin logs")
        self.current_label.setObjectName("LogCurrent")
        self.current_label.setWordWrap(True)

        self.history_button = QToolButton()
        self.history_button.setObjectName("LogHistoryButton")
        self.history_button.setText("🕘")
        self.history_button.setToolTip("Mostrar historial")
        self.history_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_button.setCheckable(True)
        self.history_button.toggled.connect(self._toggle_history)

        header.addWidget(self.current_label, 1)
        header.addWidget(self.history_button)

        container.addLayout(header)

        self.history_list = QListWidget()
        self.history_list.setObjectName("LogHistoryList")
        self.history_list.setVisible(False)
        container.addWidget(self.history_list)

        self._clear_timer = QTimer(self)
        self._clear_timer.setSingleShot(True)
        self._clear_timer.timeout.connect(self._clear_current)

    def loguear(self, texto: str):
        message = (texto or "").strip()
        if not message:
            return

        self.current_label.setText(message)
        self._history.appendleft(message)
        self._refresh_history()
        self._clear_timer.start(self.display_ms)

    def _clear_current(self):
        self.current_label.setText("Sin logs")

    def _toggle_history(self, show_history: bool):
        self.history_list.setVisible(show_history)
        self.history_button.setToolTip("Ocultar historial" if show_history else "Mostrar historial")

    def _refresh_history(self):
        self.history_list.clear()
        for message in self._history:
            self.history_list.addItem(message)
