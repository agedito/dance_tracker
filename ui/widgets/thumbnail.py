from PySide6.QtWidgets import QWidget, QSizePolicy

from ui.frames_mock import draw_thumbnail_frame


class ThumbnailWidget(QWidget):
    def __init__(self, label: str, seed: int = 1, parent=None):
        super().__init__(parent)
        self.label = label
        self.seed = seed
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, ev):
        draw_thumbnail_frame(self, self.seed, self.label)
