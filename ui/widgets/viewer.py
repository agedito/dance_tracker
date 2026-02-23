from PySide6.QtWidgets import QWidget, QSizePolicy

from app.logic import clamp
from ui.frames_mock import draw_viewer_frame


class ViewerWidget(QWidget):
    def __init__(self, total_frames: int, parent=None):
        super().__init__(parent)
        self.total_frames = total_frames
        self.frame = 0
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_frame(self, f: int):
        self.frame = clamp(f, 0, self.total_frames - 1)
        self.update()

    def paintEvent(self, ev):
        draw_viewer_frame(self, self.frame, self.total_frames)
