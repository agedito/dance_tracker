from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QResizeEvent
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QToolButton, QWidget
from shiboken6 import isValid

from app.interface.application import DanceTrackerPort
from ui.widgets.frame_store import FrameStore
from ui.widgets.drop_handler import DropHandler
from ui.widgets.radial_menu_widget import RadialMenuWidget
from ui.window.frames_mock import draw_viewer_frame
from utils.numbers import clamp


class DetectionOverlay(QWidget):
    """Toggle button overlay + bounding-box drawing for detected persons.

    Responsibilities:
      - Own the eye-icon toggle button widget (visibility + positioning)
      - Draw bounding boxes and confidence labels onto an open QPainter
    """

    repaintRequested = Signal()

    def __init__(self, track_detector, parent: QWidget) -> None:
        super().__init__(parent)
        self._track_detector = track_detector
        self._show = True

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "background-color: rgba(70, 70, 70, 150); border-radius: 12px;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        button = QToolButton(self)
        button.setCheckable(True)
        button.setChecked(True)
        button.setText("👁")
        button.setToolTip("Show or hide detections")
        button.setStyleSheet(
            "QToolButton {"
            "color: white;"
            "font-size: 15px;"
            "background: transparent;"
            "border: none;"
            "padding: 2px 4px;"
            "}"
            "QToolButton:checked { color: #6DFFB4; }"
        )
        button.toggled.connect(self._on_toggled)
        layout.addWidget(button)
        self.adjustSize()

    def reposition(self, video_rect: QRectF) -> None:
        self.adjustSize()
        size = self.sizeHint()
        margin = 10
        x = int(video_rect.right() - size.width() - margin)
        y = int(video_rect.top() + margin)
        self.setGeometry(x, y, size.width(), size.height())
        self.raise_()

    def paint(self, painter: QPainter, video_rect: QRectF, frame: int) -> None:
        if not self._show:
            return
        detections = self._track_detector.detections_for_frame(frame)
        if not detections:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)

        for detection in detections:
            rel_box = detection.bbox_relative
            x = video_rect.x() + rel_box.x * video_rect.width()
            y = video_rect.y() + rel_box.y * video_rect.height()
            w = rel_box.width * video_rect.width()
            h = rel_box.height * video_rect.height()

            rect = QRectF(x, y, w, h)
            painter.setPen(QPen(QColor(0, 220, 120), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

            label_rect = QRectF(rect.x(), max(video_rect.y(), rect.y() - 20), 88, 18)
            painter.fillRect(label_rect, QColor(0, 0, 0, 170))
            painter.setPen(QPen(QColor(0, 255, 150), 1))
            painter.drawText(
                label_rect.adjusted(4, 0, -2, 0),
                Qt.AlignmentFlag.AlignVCenter,
                f"person {detection.confidence:.2f}",
            )

        painter.restore()

    def _on_toggled(self, checked: bool) -> None:
        self._show = checked
        self.repaintRequested.emit()


class ViewerWidget(QWidget):
    """Single responsibility: render the current video frame with a border.

    Drag-and-drop is delegated to DropHandler.
    The radial menu is a child overlay widget (RadialMenuWidget).
    Detection overlay (toggle button + bounding boxes) is delegated to DetectionOverlay.
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

        # ── Detection overlay ────────────────────────────────────────
        self._detection_overlay = DetectionOverlay(app.track_detector, parent=self)
        self._detection_overlay.repaintRequested.connect(self.update)

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
        source_width = display_size[0] if display_size is not None else pixmap.width()
        source_height = display_size[1] if display_size is not None else pixmap.height()
        if source_width <= 0 or source_height <= 0:
            return QRectF(self.rect().adjusted(16, 16, -16, -16))

        widget_width = max(1, self.width())
        widget_height = max(1, self.height())
        scale = min(widget_width / source_width, widget_height / source_height)
        target_width = int(source_width * scale)
        target_height = int(source_height * scale)
        x = (widget_width - target_width) // 2
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
        self._detection_overlay.reposition(video_rect)

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

        pixmap = self._frame_store.get_frame(self._frame, use_proxy=self._use_proxy)
        video_rect = self._video_rect()

        if pixmap is not None:
            self._paint_frame(pixmap, video_rect)
        else:
            draw_viewer_frame(self, self._frame, self._total_frames)
            painter = QPainter(self)
            self._draw_border(painter, video_rect)
            self._detection_overlay.paint(painter, video_rect, self._frame)
            painter.end()

        self._sync_radial_menu_anchor(video_rect)
        self._detection_overlay.reposition(video_rect)

    def _sync_radial_menu_anchor(self, video_rect: QRectF):
        if self._is_closing or not isValid(self._radial_menu):
            return
        self._radial_menu.set_anchor_rect(video_rect)

    # ── Painting helpers ─────────────────────────────────────────────

    def _paint_frame(self, pixmap, video_rect: QRectF):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawPixmap(video_rect, pixmap, QRectF(pixmap.rect()))
        self._draw_border(painter, video_rect)
        self._detection_overlay.paint(painter, video_rect, self._frame)
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
