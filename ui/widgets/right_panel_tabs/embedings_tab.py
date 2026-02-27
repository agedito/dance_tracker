from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ui.widgets.right_panel_tabs.common import section_label


class EmbedingsTabWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section_label("Embedings"))

        info = QLabel("Sección reservada para futuras visualizaciones de embeddings.")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch(1)
