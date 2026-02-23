from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QWidget, QSizePolicy

from app.logic import clamp
from ui.frames_mock import draw_viewer_frame


class ViewerWidget(QWidget):
    layerDropped = Signal(str, int)

    def __init__(self, total_frames: int, parent=None):
        super().__init__(parent)
        self.total_frames = total_frames
        self.frame = 0
        self.layer_label = "Layer 0: Master Video"
        self.layer_seed = 1
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAcceptDrops(True)

    def set_frame(self, f: int):
        self.frame = clamp(f, 0, self.total_frames - 1)
        self.update()

    def set_layer_preview(self, label: str, seed: int):
        self.layer_label = label
        self.layer_seed = seed
        self.update()

    def dragEnterEvent(self, ev: QDragEnterEvent):
        from ui.widgets.thumbnail import ThumbnailWidget

        if ev.mimeData().hasFormat(ThumbnailWidget.MIME_TYPE):
            ev.acceptProposedAction()
            return
        ev.ignore()

    def dropEvent(self, ev: QDropEvent):
        from ui.widgets.thumbnail import ThumbnailWidget

        payload = ev.mimeData().data(ThumbnailWidget.MIME_TYPE).data().decode("utf-8")
        if "|" not in payload:
            ev.ignore()
            return

        label, seed_text = payload.rsplit("|", 1)
        if not seed_text.isdigit():
            ev.ignore()
            return

        self.layerDropped.emit(label, int(seed_text))
        ev.acceptProposedAction()

    def paintEvent(self, ev):
        draw_viewer_frame(
            self,
            self.frame,
            self.total_frames,
            self.layer_label,
            self.layer_seed,
        )
