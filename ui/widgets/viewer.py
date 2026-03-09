from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QResizeEvent
from PySide6.QtWidgets import QSizePolicy, QWidget
from shiboken6 import isValid

from app.interface.application import DanceTrackerPort
from ui.widgets.frame_store import FrameStore
from ui.widgets.drop_handler import DropHandler
from ui.widgets.radial_menu_widget import RadialMenuWidget
from ui.widgets.viewer_overlay_bar import ViewerOverlayBar
from ui.window.frames_mock import draw_viewer_frame
from utils.numbers import clamp


class ViewerWidget(QWidget):
    """Single responsibility: render the current video frame with a border.

    Drag-and-drop is delegated to DropHandler.
    The radial menu is a child overlay widget (RadialMenuWidget).
    Detection + pose overlays (toggle buttons + drawing) are handled by ViewerOverlayBar.
    """

    framesLoaded = Signal(int)
    folderLoaded = Signal(str, int)

    def __init__(self, app: DanceTrackerPort, total_frames: int, frame_store: FrameStore, parent=None):
        super().__init__(parent)
        self._total_frames = max(1, total_frames)
        self._frame = 0
        self._frame_store = frame_store
        self._use_proxy = False
        self._is_closing = False

        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAcceptDrops(True)

        # ── Radial menu overlay ──────────────────────────────────────
        self._radial_menu = RadialMenuWidget(parent=self)
        self._radial_menu.borderColorChanged.connect(self._on_border_color_changed)
        self._border_color = self._radial_menu.active_border_color

        # ── Drop handler ─────────────────────────────────────────────
        self._drop_handler = DropHandler(app.media, parent=self)
        self._drop_handler.framesLoaded.connect(self.framesLoaded)
        self._drop_handler.folderLoaded.connect(self.folderLoaded)

        # ── Overlay bar (detection + pose toggles + drawing) ─────────
        self._overlay_bar = ViewerOverlayBar(app.track_detector, app.pose_detector, parent=self)
        self._overlay_bar.repaintRequested.connect(self.update)

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
        source_width  = display_size[0] if display_size is not None else pixmap.width()
        source_height = display_size[1] if display_size is not None else pixmap.height()
        if source_width <= 0 or source_height <= 0:
            return QRectF(self.rect().adjusted(16, 16, -16, -16))

        widget_width  = max(1, self.width())
        widget_height = max(1, self.height())
        scale         = min(widget_width / source_width, widget_height / source_height)
        target_width  = int(source_width  * scale)
        target_height = int(source_height * scale)
        x = (widget_width  - target_width)  // 2
        y = (widget_height - target_height) // 2
        return QRectF(x, y, target_width, target_height)

    # ── Events ───────────────────────────────────────────────────────

    def resizeEvent(self, ev: QResizeEvent):
        super().resizeEvent(ev)
        if self._is_closing:
            return
        self._radial_menu.setGeometry(self.rect())
        video_rect = self._video_rect()
        self._sync_radial_menu_anchor(video_rect)
        self._overlay_bar.reposition(video_rect)

    def closeEvent(self, ev):
        self._is_closing = True
        if isValid(self._radial_menu):
            self._radial_menu.hide()
        super().closeEvent(ev)

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
        if self._is_closing:
            return

        pixmap    = self._frame_store.get_frame(self._frame, use_proxy=self._use_proxy)
        video_rect = self._video_rect()

        if pixmap is not None:
            self._paint_frame(pixmap, video_rect)
        else:
            draw_viewer_frame(self, self._frame, self._total_frames)
            painter = QPainter(self)
            self._draw_border(painter, video_rect)
            self._overlay_bar.paint(painter, video_rect, self._frame)
            painter.end()

        self._sync_radial_menu_anchor(video_rect)
        self._overlay_bar.reposition(video_rect)

    # ── Painting helpers ─────────────────────────────────────────────

    def _sync_radial_menu_anchor(self, video_rect: QRectF):
        if self._is_closing or not isValid(self._radial_menu):
            return
        self._radial_menu.set_anchor_rect(video_rect)

    def _paint_frame(self, pixmap, video_rect: QRectF):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawPixmap(video_rect, pixmap, QRectF(pixmap.rect()))
        self._draw_border(painter, video_rect)
        self._overlay_bar.paint(painter, video_rect, self._frame)
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
