import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget


@dataclass
class Vec3:
    x: float
    y: float
    z: float

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vec3":
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)


class Pose3DViewerWidget(QWidget):
    """Simple 3D pose viewer with orbit camera and box-based characters."""

    _LIMBS = [
        (5, 6),  # shoulders
        (11, 12),  # hips
        (5, 11),
        (6, 12),
        (5, 7),
        (7, 9),
        (6, 8),
        (8, 10),
        (11, 13),
        (13, 15),
        (12, 14),
        (14, 16),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

        self._detections: list[dict] = []
        self._yaw = 0.9
        self._pitch = -0.45
        self._distance = 7.5
        self._dragging = False
        self._last_mouse = QPointF()

    def set_detections(self, detections: list[dict]):
        self._detections = detections
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._last_mouse = QPointF(event.position())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self._dragging:
            super().mouseMoveEvent(event)
            return

        pos = QPointF(event.position())
        delta = pos - self._last_mouse
        self._last_mouse = pos

        self._yaw += delta.x() * 0.01
        self._pitch += delta.y() * 0.008
        self._pitch = max(-1.3, min(0.2, self._pitch))
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self._distance *= 0.9 if delta > 0 else 1.1
        self._distance = max(3.0, min(14.0, self._distance))
        self.update()
        event.accept()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(15, 19, 24))

        self._draw_grid(painter)

        for index, det in enumerate(self._detections):
            color = QColor(120, 190, 255) if index % 2 == 0 else QColor(255, 165, 120)
            self._draw_detection_character(painter, det, color)

        painter.setPen(QColor(190, 205, 220))
        painter.drawText(
            12,
            20,
            "Visor 3D · Arrastra para rotar · Rueda para zoom",
        )
        painter.end()

    def _camera_transform(self, point: Vec3) -> Vec3:
        cy, sy = math.cos(self._yaw), math.sin(self._yaw)
        cp, sp = math.cos(self._pitch), math.sin(self._pitch)

        # Orbit camera looking at world origin.
        cam = Vec3(0.0, 1.2, self._distance)
        x1 = point.x * cy - point.z * sy
        z1 = point.x * sy + point.z * cy
        y1 = point.y

        y2 = y1 * cp - z1 * sp
        z2 = y1 * sp + z1 * cp

        return Vec3(x1 - cam.x, y2 - cam.y, z2 - cam.z)

    def _project(self, point: Vec3) -> tuple[QPointF | None, float]:
        cam_p = self._camera_transform(point)
        depth = -cam_p.z
        if depth <= 0.05:
            return None, depth

        focal = min(self.width(), self.height()) * 0.75
        sx = (cam_p.x * focal / depth) + self.width() / 2
        sy = (-cam_p.y * focal / depth) + self.height() / 2
        return QPointF(sx, sy), depth

    def _draw_grid(self, painter: QPainter):
        painter.setPen(QPen(QColor(95, 105, 115), 1))
        span = 8
        for i in range(-span, span + 1):
            a, _ = self._project(Vec3(i * 0.5, 0, -span * 0.5))
            b, _ = self._project(Vec3(i * 0.5, 0, span * 0.5))
            if a and b:
                painter.drawLine(a, b)

            c, _ = self._project(Vec3(-span * 0.5, 0, i * 0.5))
            d, _ = self._project(Vec3(span * 0.5, 0, i * 0.5))
            if c and d:
                painter.drawLine(c, d)

        painter.setPen(QPen(QColor(160, 170, 180), 2))
        x0, _ = self._project(Vec3(-4, 0, 0))
        x1, _ = self._project(Vec3(4, 0, 0))
        z0, _ = self._project(Vec3(0, 0, -4))
        z1, _ = self._project(Vec3(0, 0, 4))
        if x0 and x1:
            painter.drawLine(x0, x1)
        if z0 and z1:
            painter.drawLine(z0, z1)

    def _draw_detection_character(self, painter: QPainter, detection: dict, color: QColor):
        points = self._extract_keypoints(detection)
        if not points:
            return

        body_segments = []
        for a, b in self._LIMBS:
            pa = points.get(a)
            pb = points.get(b)
            if pa and pb:
                body_segments.append((pa, pb))

        for start, end in body_segments:
            self._draw_limb_box(painter, start, end, color)

        nose = points.get(0)
        l_shoulder = points.get(5)
        r_shoulder = points.get(6)
        if nose:
            self._draw_box(painter, nose + Vec3(-0.08, -0.05, -0.08), nose + Vec3(0.08, 0.11, 0.08), color)
        elif l_shoulder and r_shoulder:
            center = Vec3((l_shoulder.x + r_shoulder.x) * 0.5, l_shoulder.y + 0.22, (l_shoulder.z + r_shoulder.z) * 0.5)
            self._draw_box(painter, center + Vec3(-0.1, -0.1, -0.1), center + Vec3(0.1, 0.1, 0.1), color)

    def _draw_limb_box(self, painter: QPainter, a: Vec3, b: Vec3, color: QColor):
        min_x = min(a.x, b.x) - 0.05
        max_x = max(a.x, b.x) + 0.05
        min_y = min(a.y, b.y) - 0.05
        max_y = max(a.y, b.y) + 0.05
        min_z = min(a.z, b.z) - 0.05
        max_z = max(a.z, b.z) + 0.05
        self._draw_box(painter, Vec3(min_x, min_y, min_z), Vec3(max_x, max_y, max_z), color)

    def _draw_box(self, painter: QPainter, pmin: Vec3, pmax: Vec3, color: QColor):
        corners = [
            Vec3(pmin.x, pmin.y, pmin.z),
            Vec3(pmax.x, pmin.y, pmin.z),
            Vec3(pmax.x, pmax.y, pmin.z),
            Vec3(pmin.x, pmax.y, pmin.z),
            Vec3(pmin.x, pmin.y, pmax.z),
            Vec3(pmax.x, pmin.y, pmax.z),
            Vec3(pmax.x, pmax.y, pmax.z),
            Vec3(pmin.x, pmax.y, pmax.z),
        ]

        projected = []
        depths = []
        for corner in corners:
            screen, depth = self._project(corner)
            if screen is None:
                return
            projected.append(screen)
            depths.append(depth)

        faces = [
            (0, 1, 2, 3),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (2, 3, 7, 6),
            (1, 2, 6, 5),
            (0, 3, 7, 4),
        ]

        sorted_faces = sorted(faces, key=lambda face: sum(depths[i] for i in face) / 4, reverse=True)
        for face in sorted_faces:
            poly = QPolygonF([projected[i] for i in face])
            shade = 0.65 + (sum(depths[i] for i in face) / (4 * max(depths))) * 0.35
            shaded = QColor(
                min(255, int(color.red() * shade)),
                min(255, int(color.green() * shade)),
                min(255, int(color.blue() * shade)),
                180,
            )
            painter.setPen(QPen(QColor(25, 32, 40, 210), 1))
            painter.setBrush(shaded)
            painter.drawPolygon(poly)

    @staticmethod
    def _extract_keypoints(detection: dict) -> dict[int, Vec3]:
        keypoints = detection.get("keypoints", [])
        flat: list[float] = []
        if keypoints and isinstance(keypoints[0], (list, tuple)):
            for kp in keypoints:
                if len(kp) >= 3:
                    flat.extend([kp[0], kp[1], kp[2]])
        elif keypoints:
            flat = keypoints

        points: dict[int, Vec3] = {}
        for index in range(min(17, len(flat) // 3)):
            x = float(flat[index * 3])
            y = float(flat[index * 3 + 1])
            conf = float(flat[index * 3 + 2])
            if conf < 0.2:
                continue
            world_x = (x - 0.5) * 3.2
            world_y = (1.0 - y) * 2.2
            world_z = 0.0
            points[index] = Vec3(world_x, world_y, world_z)

        return points
