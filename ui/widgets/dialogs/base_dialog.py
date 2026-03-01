from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QProgressDialog, QWidget


class BaseDialog(QDialog):
    """Base class for every dialog shown by the UI."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._apply_default_config()

    def _apply_default_config(self) -> None:
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)


class BaseProgressDialog(QProgressDialog):
    """Base progress dialog used by long-running actions in the UI."""

    def __init__(
        self,
        label_text: str,
        cancel_button_text: str,
        minimum: int,
        maximum: int,
        parent: QWidget | None = None,
    ):
        super().__init__(label_text, cancel_button_text, minimum, maximum, parent)
        self._apply_default_config()

    def _apply_default_config(self) -> None:
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setMinimumDuration(0)
        self.setAutoClose(True)
        self.setAutoReset(True)
