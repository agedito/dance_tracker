"""Combined detection + pose + segmentation toggle bar rendered over the video frame."""

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QWidget

_ICON_PX = 30   # icon pixmap side length
_BTN_SIZE = 38  # button bounding box (icon + padding)

# ── Icon factories ────────────────────────────────────────────────────────────

def _detection_icon(active: bool) -> QIcon:
    """Two non-intersecting rounded rectangles (teal + amber)."""
    s = _ICON_PX
    px = QPixmap(s, s)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    if active:
        c1, f1 = QColor(0, 210, 170), QColor(0, 210, 170, 60)
        c2, f2 = QColor(255, 145, 35), QColor(255, 145, 35, 60)
        pw = 2.0
    else:
        c1 = c2 = QColor(120, 125, 132, 150)
        f1 = f2 = QColor(120, 125, 132, 22)
        pw = 1.5

    # Upper-left rect
    p.setPen(QPen(c1, pw))
    p.setBrush(f1)
    p.drawRoundedRect(QRectF(1.5, 3.0, s * 0.54, s * 0.46), 3, 3)

    # Lower-right rect (clearly separated)
    p.setPen(QPen(c2, pw))
    p.setBrush(f2)
    p.drawRoundedRect(QRectF(s * 0.44, s * 0.50, s * 0.54, s * 0.46), 3, 3)

    p.end()
    return QIcon(px)


def _pose_icon(active: bool) -> QIcon:
    """Stick figure: head + body line + two arms + two legs."""
    s = _ICON_PX
    px = QPixmap(s, s)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    color = QColor(165, 80, 255) if active else QColor(120, 125, 132, 150)
    pen = QPen(color, 2.0 if active else 1.6,
               Qt.PenStyle.SolidLine,
               Qt.PenCapStyle.RoundCap,
               Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(color if active else QColor(120, 125, 132, 150))

    cx = s / 2.0

    # Head
    hr = s * 0.11
    head_cy = s * 0.14
    p.drawEllipse(QRectF(cx - hr, head_cy - hr, hr * 2, hr * 2))

    p.setBrush(Qt.BrushStyle.NoBrush)

    # Body (neck → hip)
    neck_y = head_cy + hr
    hip_y  = s * 0.62
    p.drawLine(QPointF(cx, neck_y), QPointF(cx, hip_y))

    # Shoulder position
    sh_y = neck_y + (hip_y - neck_y) * 0.30

    # Left arm — raised
    p.drawLine(QPointF(cx, sh_y), QPointF(cx - s * 0.30, sh_y - s * 0.24))
    # Right arm — extended sideways-down
    p.drawLine(QPointF(cx, sh_y), QPointF(cx + s * 0.30, sh_y + s * 0.12))

    # Left leg
    p.drawLine(QPointF(cx, hip_y), QPointF(cx - s * 0.20, s * 0.93))
    # Right leg
    p.drawLine(QPointF(cx, hip_y), QPointF(cx + s * 0.20, s * 0.93))

    p.end()
    return QIcon(px)


def _segmentation_icon(active: bool) -> QIcon:
    """Person silhouette: filled shape with a vertical split — left darkened, right bright."""
    s = _ICON_PX
    px = QPixmap(s, s)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    if active:
        bg_color     = QColor(30, 30, 40, 180)
        person_color = QColor(255, 180, 40, 230)
        dim_color    = QColor(80, 80, 90, 180)
    else:
        bg_color     = QColor(60, 60, 70, 80)
        person_color = QColor(120, 125, 132, 120)
        dim_color    = QColor(60, 60, 70, 80)

    cx = s / 2.0

    # Background rectangle
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(bg_color)
    p.drawRoundedRect(QRectF(1, 1, s - 2, s - 2), 3, 3)

    # Person silhouette — right half (bright = inside mask)
    p.setBrush(person_color)
    p.setClipRect(QRectF(cx, 0, s, s))
    _draw_silhouette(p, s, cx)

    # Person silhouette — left half (dim = outside mask)
    p.setBrush(dim_color)
    p.setClipRect(QRectF(0, 0, cx, s))
    _draw_silhouette(p, s, cx)

    p.setClipping(False)
    p.end()
    return QIcon(px)


def _draw_silhouette(p: QPainter, s: float, cx: float) -> None:
    """Draw a simple body silhouette (head + torso/legs block) centered at cx."""
    hr = s * 0.10
    head_cy = s * 0.15
    # Head
    p.drawEllipse(QRectF(cx - hr, head_cy - hr, hr * 2, hr * 2))
    # Body block
    body_top = head_cy + hr
    p.drawRoundedRect(
        QRectF(cx - s * 0.18, body_top, s * 0.36, s * 0.78),
        s * 0.06, s * 0.06,
    )


# ── Skeleton drawing constants (MediaPipe 33 landmarks) ───────────────────────

_POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12),
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (27, 31), (29, 31),
    (24, 26), (26, 28), (28, 30), (28, 32), (30, 32),
]
_LEFT_LM  = {1, 2, 3, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31}
_RIGHT_LM = {4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32}
_C_LEFT   = QColor(130, 80, 255, 210)
_C_RIGHT  = QColor(255, 80, 160, 210)
_C_MID    = QColor(200, 180, 255, 200)
_VIS_THR  = 0.5
_PT_R     = 3.0

_SEG_DARKEN = QColor(0, 0, 0, 160)  # overlay color for non-masked areas


def _lm_color(idx: int) -> QColor:
    if idx in _LEFT_LM:  return _C_LEFT
    if idx in _RIGHT_LM: return _C_RIGHT
    return _C_MID


def _conn_color(a: int, b: int) -> QColor:
    if a in _LEFT_LM  and b in _LEFT_LM:  return _C_LEFT
    if a in _RIGHT_LM and b in _RIGHT_LM: return _C_RIGHT
    return _C_MID


# ── Combined overlay bar ──────────────────────────────────────────────────────

_BTN_STYLE = (
    "QToolButton {"
    "  background: transparent;"
    "  border: none;"
    "  border-radius: 7px;"
    "  padding: 3px;"
    "}"
    "QToolButton:hover {"
    "  background: rgba(255,255,255,22);"
    "}"
    "QToolButton:checked {"
    "  background: rgba(255,255,255,14);"
    "}"
)


class ViewerOverlayBar(QWidget):
    """Horizontal bar with detection + pose + segmentation toggle buttons, placed top-right of video.

    Also owns the paint logic for all three overlays so the viewer calls a single
    ``paint()`` method.
    """

    repaintRequested = Signal()

    def __init__(self, track_detector, pose_detector, segmentation, parent: QWidget) -> None:
        super().__init__(parent)
        self._track_detector  = track_detector
        self._pose_detector   = pose_detector
        self._segmentation    = segmentation
        self._show_detections = True
        self._show_poses      = True
        self._show_segmentation = True

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "ViewerOverlayBar {"
            "  background-color: rgba(22, 24, 30, 185);"
            "  border-radius: 10px;"
            "}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 4, 5, 4)
        layout.setSpacing(2)

        self._btn_det  = self._build_button(_detection_icon,   "Show / hide bounding box detections", self._on_detection_toggled)
        self._btn_pose = self._build_button(_pose_icon,        "Show / hide pose skeleton",            self._on_pose_toggled)
        self._btn_seg  = self._build_button(_segmentation_icon,"Show / hide segmentation mask",        self._on_segmentation_toggled)
        layout.addWidget(self._btn_det)
        layout.addWidget(self._btn_pose)
        layout.addWidget(self._btn_seg)

        self.adjustSize()

    # ── Public ───────────────────────────────────────────────────────────────

    def reposition(self, video_rect: QRectF) -> None:
        self.adjustSize()
        sz = self.sizeHint()
        x  = int(video_rect.right() - sz.width() - 10)
        y  = int(video_rect.top()   + 10)
        self.setGeometry(x, y, sz.width(), sz.height())
        self.raise_()

    def paint(self, painter: QPainter, video_rect: QRectF, frame: int) -> None:
        if self._show_segmentation:
            self._paint_segmentation(painter, video_rect, frame)
        if self._show_detections:
            self._paint_detections(painter, video_rect, frame)
        if self._show_poses:
            self._paint_poses(painter, video_rect, frame)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _build_button(self, icon_fn, tooltip: str, slot) -> QToolButton:
        btn = QToolButton(self)
        btn.setCheckable(True)
        btn.setChecked(True)
        btn.setFixedSize(_BTN_SIZE, _BTN_SIZE)
        btn.setIconSize(QSize(_ICON_PX, _ICON_PX))
        btn.setIcon(icon_fn(True))
        btn.setToolTip(tooltip)
        btn.setStyleSheet(_BTN_STYLE)
        btn.toggled.connect(lambda checked, fn=icon_fn: btn.setIcon(fn(checked)))
        btn.toggled.connect(slot)
        return btn

    def _on_detection_toggled(self, checked: bool) -> None:
        self._show_detections = checked
        self.repaintRequested.emit()

    def _on_pose_toggled(self, checked: bool) -> None:
        self._show_poses = checked
        self.repaintRequested.emit()

    def _on_segmentation_toggled(self, checked: bool) -> None:
        self._show_segmentation = checked
        self.repaintRequested.emit()

    def _paint_detections(self, painter: QPainter, video_rect: QRectF, frame: int) -> None:
        detections = self._track_detector.detections_for_frame(frame)
        if not detections:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        for det in detections:
            rb  = det.bbox_relative
            x   = video_rect.x() + rb.x * video_rect.width()
            y   = video_rect.y() + rb.y * video_rect.height()
            w   = rb.width  * video_rect.width()
            h   = rb.height * video_rect.height()
            rect = QRectF(x, y, w, h)
            painter.setPen(QPen(QColor(0, 220, 120), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            label = QRectF(rect.x(), max(video_rect.y(), rect.y() - 20), 88, 18)
            painter.fillRect(label, QColor(0, 0, 0, 170))
            painter.setPen(QPen(QColor(0, 255, 150), 1))
            painter.drawText(label.adjusted(4, 0, -2, 0),
                             Qt.AlignmentFlag.AlignVCenter,
                             f"person {det.confidence:.2f}")
        painter.restore()

    def _paint_poses(self, painter: QPainter, video_rect: QRectF, frame: int) -> None:
        poses = self._pose_detector.poses_for_frame(frame)
        if not poses:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for pose in poses:
            lm_map = {lm.index: lm for lm in pose.landmarks}
            # Connections
            for a_idx, b_idx in _POSE_CONNECTIONS:
                a = lm_map.get(a_idx)
                b = lm_map.get(b_idx)
                if a is None or b is None:
                    continue
                if a.visibility < _VIS_THR or b.visibility < _VIS_THR:
                    continue
                ax = video_rect.x() + a.x * video_rect.width()
                ay = video_rect.y() + a.y * video_rect.height()
                bx = video_rect.x() + b.x * video_rect.width()
                by = video_rect.y() + b.y * video_rect.height()
                painter.setPen(QPen(_conn_color(a_idx, b_idx), 1.5))
                painter.drawLine(QPointF(ax, ay), QPointF(bx, by))
            # Points
            painter.setPen(Qt.PenStyle.NoPen)
            for lm in pose.landmarks:
                if lm.visibility < _VIS_THR:
                    continue
                lx = video_rect.x() + lm.x * video_rect.width()
                ly = video_rect.y() + lm.y * video_rect.height()
                painter.setBrush(_lm_color(lm.index))
                painter.drawEllipse(QRectF(lx - _PT_R, ly - _PT_R, _PT_R * 2, _PT_R * 2))
        painter.restore()

    def _paint_segmentation(self, painter: QPainter, video_rect: QRectF, frame: int) -> None:
        result = self._segmentation.segmentation_for_frame(frame)
        if result is None or not result.mask_path:
            return

        mask_path = Path(result.mask_path)
        if not mask_path.exists():
            return

        mask_image = QImage(str(mask_path))
        if mask_image.isNull():
            return

        painter.save()

        vx = int(video_rect.x())
        vy = int(video_rect.y())
        vw = int(video_rect.width())
        vh = int(video_rect.height())

        # Scale mask to video display size
        scaled_mask = mask_image.scaled(
            vw, vh,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ).convertToFormat(QImage.Format.Format_ARGB32)

        # Build a dark overlay pixmap the size of the video area,
        # then punch holes where the mask says "person" (non-black pixels).
        overlay = QPixmap(vw, vh)
        overlay.fill(_SEG_DARKEN)

        overlay_painter = QPainter(overlay)
        overlay_painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_DestinationOut
        )
        # Draw the mask: white=person → erases dark overlay → video shows through
        # Black=background → overlay stays → video is darkened
        overlay_painter.drawImage(0, 0, scaled_mask)
        overlay_painter.end()

        painter.drawPixmap(vx, vy, overlay)
        painter.restore()
