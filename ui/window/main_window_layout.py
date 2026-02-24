from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget


class MainWindowLayout:
    """Estructura base del layout principal sin lógica de widgets."""

    def __init__(self, parent):
        self.root = QWidget(parent)

        self.outer = QVBoxLayout(self.root)
        self.outer.setContentsMargins(10, 10, 10, 10)
        self.outer.setSpacing(10)

        self.top_splitter = QSplitter(Qt.Horizontal)
        self.top_splitter.setChildrenCollapsible(False)

        self.bottom_splitter = QSplitter(Qt.Horizontal)
        self.bottom_splitter.setChildrenCollapsible(False)

        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.addWidget(self.top_splitter)
        self.main_splitter.addWidget(self.bottom_splitter)
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 2)
        self.main_splitter.setSizes([470, 300])

    def set_topbar(self, widget: QWidget):
        self.outer.addWidget(widget)

    def set_top_content(self, left: QWidget, right: QWidget):
        self.top_splitter.addWidget(left)
        self.top_splitter.addWidget(right)
        self.top_splitter.setStretchFactor(0, 3)
        self.top_splitter.setStretchFactor(1, 2)
        self.top_splitter.setSizes([720, 480])

    def set_bottom_content(self, left: QWidget, right: QWidget):
        self.bottom_splitter.addWidget(left)
        self.bottom_splitter.addWidget(right)
        self.bottom_splitter.setStretchFactor(0, 4)
        self.bottom_splitter.setStretchFactor(1, 2)
        self.bottom_splitter.setSizes([800, 400])

    def finalize(self):
        self.outer.addWidget(self.main_splitter, 1)
