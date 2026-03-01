from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QProgressDialog, QWidget


class BaseDialog(QDialog):
    """Base dialog with shared defaults for the application."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._apply_defaults()

    def _apply_defaults(self) -> None:
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)


class BaseProgressDialog(QProgressDialog):
    """Progress dialog that keeps the same look and behavior as BaseDialog."""

    def __init__(
        self,
        label_text: str,
        cancel_button_text: str,
        minimum: int,
        maximum: int,
        parent: QWidget | None = None,
    ):
        super().__init__(label_text, cancel_button_text, minimum, maximum, parent)
        self._apply_defaults()

    def _apply_defaults(self) -> None:
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setMinimumDuration(0)
        self.setAutoClose(True)
        self.setAutoReset(True)
