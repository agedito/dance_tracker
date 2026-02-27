from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class TopBar(QWidget):
    """Render a minimal top bar without media shortcuts or previews."""

    def __init__(self, on_close):
        super().__init__()

        self.setObjectName("TopBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        title = QLabel("MAIN VIEWER")
        title.setObjectName("TopTitle")
        layout.addWidget(title)

        layout.addStretch(1)

        close_button = QPushButton("✕")
        close_button.setObjectName("TopCloseButton")
        close_button.setToolTip("Close app")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(on_close)
        layout.addSpacing(10)
        layout.addWidget(close_button)

    def refresh_icons(self):
        """Compatibility no-op: top bar no longer shows recent media."""

    def set_active_folder(self, folder_path):
        """Compatibility no-op: top bar no longer tracks folders."""
