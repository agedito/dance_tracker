from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QGroupBox, QToolButton, QVBoxLayout, QWidget


class CollapsibleSection(QWidget):
    """Expandable/collapsible section with a toggle button and a form layout body."""

    def __init__(self, title: str):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._toggle = QToolButton(self)
        self._toggle.setText(title)
        self._toggle.setCheckable(True)
        self._toggle.setChecked(True)
        self._toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle.setArrowType(Qt.ArrowType.DownArrow)
        self._toggle.toggled.connect(self._on_toggled)

        self._content = QGroupBox(self)
        self._content_layout = QFormLayout(self._content)
        self._content_layout.setContentsMargins(8, 12, 8, 8)

        layout.addWidget(self._toggle)
        layout.addWidget(self._content)

    @property
    def form_layout(self) -> QFormLayout:
        return self._content_layout

    def _on_toggled(self, expanded: bool) -> None:
        self._toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self._content.setVisible(expanded)
