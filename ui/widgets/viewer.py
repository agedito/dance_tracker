import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.frame_store import FrameStore
from ui.frames_mock import draw_viewer_frame
from utils.numbers import clamp


class ViewerWidget(QWidget):
    framesLoaded = Signal(int)

    def __init__(self, total_frames: int, frame_store: FrameStore, parent=None):
        super().__init__(parent)
        self.total_frames = total_frames
        self.frame = 0
        self.frame_store = frame_store
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAcceptDrops(True)

        self.menu_expanded = False
        self.menu_icon_count = 8
        self.menu_rotation = 0.0
        self.selected_icon = 0
        self._dragging_menu = False
        self._last_drag_angle = 0.0

    def set_total_frames(self, total_frames: int):
        self.total_frames = max(1, total_frames)
        self.frame = clamp(self.frame, 0, self.total_frames - 1)
        self.update()

    def set_frame(self, f: int):
        self.frame = clamp(f, 0, self.total_frames - 1)
        self.update()

    @staticmethod
    def _angle_from_center(pos: QPointF, center: QPointF) -> float:
        return math.atan2(pos.y() - center.y(), pos.x() - center.x())

    def _video_rect(self) -> QRectF:
        pixmap = self.frame_store.get_frame(self.frame)
        if pixmap is None:
            return QRectF(self.rect().adjusted(16, 16, -16, -16))

        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        return QRectF(x, y, scaled.width(), scaled.height())

    def _menu_center(self, video_rect: QRectF) -> QPointF:
        return QPointF(video_rect.right() - 38, video_rect.bottom() - 38)

    def _menu_item_centers(self, center: QPointF):
        radius = 102.0
        step = (2 * math.pi) / self.menu_icon_count
        points = []
        for i in range(self.menu_icon_count):
            angle = self.menu_rotation + (i * step)
            points.append(QPointF(center.x() + math.cos(angle) * radius, center.y() + math.sin(angle) * radius))
        return points

    @staticmethod
    def _point_in_circle(point: QPointF, center: QPointF, radius: float) -> bool:
        dx = point.x() - center.x()
        dy = point.y() - center.y()
        return (dx * dx + dy * dy) <= radius * radius

    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls() and any(url.isLocalFile() for url in ev.mimeData().urls()):
            ev.acceptProposedAction()
            return
        ev.ignore()

    def dropEvent(self, ev):
        for url in ev.mimeData().urls():
            if not url.isLocalFile():
                continue
            frame_count = self.frame_store.load_folder(url.toLocalFile())
            if frame_count > 0:
                self.framesLoaded.emit(frame_count)
                ev.acceptProposedAction()
                return
        ev.ignore()

    def mousePressEvent(self, ev):
        if ev.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(ev)
            return

        video_rect = self._video_rect()
        center = self._menu_center(video_rect)
        click_pos = QPointF(ev.position())

        if self._point_in_circle(click_pos, center, 28):
            self.menu_expanded = not self.menu_expanded
            self._dragging_menu = False
            self.update()
            return

        if self.menu_expanded:
            ring_distance = math.hypot(click_pos.x() - center.x(), click_pos.y() - center.y())

            for index, icon_center in enumerate(self._menu_item_centers(center)):
                if self._point_in_circle(click_pos, icon_center, 20) and video_rect.contains(icon_center):
                    self.selected_icon = index
                    self.update()
                    ev.accept()
                    return

            if 32 <= ring_distance <= 144:
                self._dragging_menu = True
                self._last_drag_angle = self._angle_from_center(click_pos, center)
                ev.accept()
                return

        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if not self.menu_expanded or not self._dragging_menu:
            super().mouseMoveEvent(ev)
            return

        center = self._menu_center(self._video_rect())
        current_angle = self._angle_from_center(QPointF(ev.position()), center)
        self.menu_rotation += current_angle - self._last_drag_angle
        self._last_drag_angle = current_angle
        self.update()
        ev.accept()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._dragging_menu = False
        super().mouseReleaseEvent(ev)

    def paintEvent(self, ev):
        pixmap = self.frame_store.get_frame(self.frame)
        video_rect = self._video_rect()
        if pixmap is not None:
            painter = QPainter(self)
            painter.fillRect(self.rect(), Qt.GlobalColor.black)
            scaled = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            self._draw_radial_menu(painter, video_rect)
            painter.end()
            return

        draw_viewer_frame(self, self.frame, self.total_frames)

        painter = QPainter(self)
        self._draw_radial_menu(painter, video_rect)
        painter.end()

    def _draw_radial_menu(self, painter: QPainter, video_rect: QRectF):
        center = self._menu_center(video_rect)

        if self.menu_expanded:
            painter.save()
            painter.setClipRect(video_rect)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            wheel_pen = QPen(QColor(116, 200, 255, 145), 2)
            painter.setPen(wheel_pen)
            painter.setBrush(QColor(22, 30, 38, 80))
            painter.drawEllipse(center, 103, 103)

            symbols = ["♪", "⏺", "⚑", "✂", "⏱", "↺", "★", "◎"]
            for index, icon_center in enumerate(self._menu_item_centers(center)):
                is_selected = index == self.selected_icon
                bg = QColor(65, 122, 214, 220) if is_selected else QColor(27, 33, 42, 210)
                border = QColor(157, 210, 255, 240) if is_selected else QColor(120, 160, 190, 180)
                painter.setPen(QPen(border, 1.5))
                painter.setBrush(bg)
                painter.drawEllipse(icon_center, 20, 20)

                painter.setPen(QColor(239, 246, 255))
                text_rect = QRectF(icon_center.x() - 10, icon_center.y() - 10, 20, 20)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, symbols[index])

            painter.restore()

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor(170, 220, 255), 1.5))
        painter.setBrush(QColor(35, 52, 71, 225))
        painter.drawEllipse(center, 28, 28)
        painter.setPen(QColor(234, 247, 255))
        painter.drawText(
            QRectF(center.x() - 15, center.y() - 15, 30, 30),
            Qt.AlignmentFlag.AlignCenter,
            "☰" if not self.menu_expanded else "×",
        )
        painter.restore()
