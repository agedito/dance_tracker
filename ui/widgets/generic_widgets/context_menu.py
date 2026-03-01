from PySide6.QtWidgets import QMenu, QWidget


class ContextMenuWidget(QMenu):
    """Base context menu widget used across the UI for a consistent look."""

    _STYLE_SHEET = """
        QMenu {
            background-color: #1A1F23;
            border: 1px solid #2B343B;
            padding: 4px;
        }
        QMenu::item {
            padding: 6px 12px;
            border-radius: 4px;
        }
        QMenu::item:selected {
            background-color: #3A3F45;
        }
        QMenu::separator {
            height: 1px;
            background: #4B525A;
            margin: 6px 4px;
        }
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(self._STYLE_SHEET)
