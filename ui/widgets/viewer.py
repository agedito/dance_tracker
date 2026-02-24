from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QResizeEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.frame_state.frame_store import FrameStore
from ui.widgets.drop_handler import DropHandler
from ui.widgets.radial_menu_widget import RadialMenuWidget
from ui.window.frames_mock import draw_viewer_frame
from utils.numbers import clamp


class ViewerWidget(QWidget):
    """Single responsibility: render the current video frame with a border.

    Drag-and-drop is delegated to DropHandler.
    The radial menu is a child overlay widget (RadialMenuWidget).
    """

    framesLoaded = Signal(int)
    folderLoaded = Signal(str, int)

    def __init__(self, total_frames: int, frame_store: FrameStore, parent=None):
        super().__init__(parent)
        self._total_frames = max(1, total_frames)
        self._frame = 0
        self._frame_store = frame_store
        self._use_proxy = False

        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAcceptDrops(True)

        # ── Radial menu overlay ──────────────────────────────────────
        self._radial_menu = RadialMenuWidget(parent=self)
        self._radial_menu.borderColorChanged.connect(self._on_border_color_changed)
        self._border_color = self._radial_menu.active_border_color

        # ── Drop handler ─────────────────────────────────────────────
        self._drop_handler = DropHandler(frame_store, parent=self)
        self._drop_handler.framesLoaded.connect(self.framesLoaded)
        self._drop_handler.folderLoaded.connect(self.folderLoaded)

    # ── Public API ───────────────────────────────────────────────────

    @property
    def frame_store(self) -> FrameStore:
        return self._frame_store

    def set_total_frames(self, total_frames: int):
        self._total_frames = max(1, total_frames)
        self._frame = clamp(self._frame, 0, self._total_frames - 1)
        self.update()

    def set_frame(self, f: int):
        self._frame = clamp(f, 0, self._total_frames - 1)
        self.update()

    def set_proxy_frames_enabled(self, enabled: bool):
        use_proxy = enabled and self._frame_store.has_proxy_frames
        if self._use_proxy == use_proxy:
            return
        self._use_proxy = use_proxy
        self.update()

    # ── Video rect calculation ───────────────────────────────────────

    def _video_rect(self) -> QRectF:
        pixmap = self._frame_store.get_frame(self._frame, use_proxy=self._use_proxy)
        if pixmap is None:
            return QRectF(self.rect().adjusted(16, 16, -16, -16))

        display_size = self._frame_store.get_display_size(self._frame)
        if display_size is None:
            display_size = (pixmap.width(), pixmap.height())

        pixmap = pixmap.scaled(
            display_size[0],
            display_size[1],
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        return QRectF(x, y, scaled.width(), scaled.height())

    # ── Events ───────────────────────────────────────────────────────

    def resizeEvent(self, ev: QResizeEvent):
        super().resizeEvent(ev)
        self._radial_menu.setGeometry(self.rect())
        self._radial_menu.set_anchor_rect(self._video_rect())

    def dragEnterEvent(self, ev):
        if self._drop_handler.can_accept(ev):
            ev.acceptProposedAction()
        else:
            ev.ignore()

    def dropEvent(self, ev):
        if self._drop_handler.handle_drop(ev):
            ev.acceptProposedAction()
        else:
            ev.ignore()

    def paintEvent(self, ev):
        pixmap = self._frame_store.get_frame(self._frame, use_proxy=self._use_proxy)
        video_rect = self._video_rect()

        if pixmap is not None:
            self._paint_frame(pixmap, video_rect)
        else:
            draw_viewer_frame(self, self._frame, self._total_frames)
            painter = QPainter(self)
            self._draw_border(painter, video_rect)
            painter.end()

        # Keep the radial menu in sync with the current video rect
        self._radial_menu.set_anchor_rect(video_rect)

    # ── Painting helpers ─────────────────────────────────────────────

    def _paint_frame(self, pixmap, video_rect: QRectF):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        display_size = self._frame_store.get_display_size(self._frame)
        if display_size is not None:
            pixmap = pixmap.scaled(
                display_size[0],
                display_size[1],
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        self._draw_border(painter, video_rect)
        painter.end()

    def _draw_border(self, painter: QPainter, video_rect: QRectF):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(self._border_color, 4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(video_rect.adjusted(1, 1, -1, -1))
        painter.restore()

    # ── Slots ────────────────────────────────────────────────────────

    def _on_border_color_changed(self, color: QColor):
        self._border_color = color
        self.update()
