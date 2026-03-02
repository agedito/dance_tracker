from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QProgressDialog, QWidget


class BaseDialog(QDialog):
    """Shared base class for all dialogs shown in the UI."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModal)


class BaseProgressDialog(QProgressDialog):
    """Progress dialog built on top of the shared dialog defaults."""

    def __init__(
            self,
            label_text: str,
            cancel_button_text: str,
            minimum: int,
            maximum: int,
            parent: QWidget | None = None,
    ):
        super().__init__(label_text, cancel_button_text, minimum, maximum, parent)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModal)
        self.setAutoClose(True)
        self.setAutoReset(True)
        self.setMinimumDuration(0)
