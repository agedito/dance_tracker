from PySide6.QtCore import QPointF, Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF

from app.interface.layers import Segment
from app.interface.sequence_data import Bookmark
from ui.widgets.timeline_viewport import TimelineViewport
from utils.numbers import clamp


def _status_color(t: str) -> QColor:
    _ = t
    return QColor(0, 0, 0, 220)


class TimelineTrackPainter:
    """Pure painting functions for TimelineTrack. Stateless — takes all inputs as parameters."""

    @staticmethod
    def paint(
        painter: QPainter,
        width: int,
        height: int,
        total_frames: int,
        frame: int,
        viewport: TimelineViewport,
        segments: list[Segment],
        loaded_flags: list[bool],
        bookmarks: list[Bookmark],
        dragging: bool,
        drag_source: int | None,
        drag_target: int | None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.setBrush(QColor(12, 15, 18))
        painter.setPen(QPen(QColor(43, 52, 59), 1))
        painter.drawRoundedRect(QRectF(0.5, 0.5, width - 1, height - 1), 9, 9)

        total = max(1, total_frames - 1)
        for s in segments:
            left_norm = clamp(s.a / total, 0.0, 1.0)
            right_norm = clamp(s.b / total, 0.0, 1.0)
            if right_norm < viewport.view_start or left_norm > viewport.visible_end:
                continue
            left = int(((left_norm - viewport.view_start) / max(0.0001, viewport.view_span)) * width)
            right = int(((right_norm - viewport.view_start) / max(0.0001, viewport.view_span)) * width)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_status_color(s.t))
            painter.drawRect(QRectF(left, 12, max(1, right - left), height - 16))

        TimelineTrackPainter._draw_loaded_indicator(painter, width, height, total_frames, loaded_flags, viewport)
        TimelineTrackPainter._draw_bookmarks(
            painter, bookmarks, total_frames, width, viewport, dragging, drag_source, drag_target
        )

        frame_norm = frame / max(1, total_frames - 1)
        xph = int(((frame_norm - viewport.view_start) / max(0.0001, viewport.view_span)) * width)
        painter.setPen(QPen(QColor(255, 80, 80, 240), 2))
        painter.drawLine(xph, -4, xph, height + 4)

    @staticmethod
    def _draw_loaded_indicator(
        painter: QPainter,
        w: int,
        h: int,
        total_frames: int,
        loaded_flags: list[bool],
        viewport: TimelineViewport,
    ) -> None:
        bar_h = 3
        y = h - bar_h - 1
        painter.setPen(Qt.PenStyle.NoPen)

        if w <= 1:
            loaded = bool(loaded_flags and loaded_flags[0])
            painter.setBrush(QColor(42, 160, 88, 240) if loaded else QColor(95, 98, 102, 200))
            painter.drawRect(QRectF(1, y, max(1, w - 2), bar_h))
            return

        for x in range(1, w - 1):
            norm_pos = viewport.view_start + (x / max(1, w - 1)) * viewport.view_span
            f = int(clamp(norm_pos, 0.0, 1.0) * (total_frames - 1))
            loaded = loaded_flags[f] if f < len(loaded_flags) else False
            painter.setBrush(QColor(42, 160, 88, 240) if loaded else QColor(95, 98, 102, 200))
            painter.drawRect(QRectF(x, y, 1, bar_h))

    @staticmethod
    def _draw_bookmarks(
        painter: QPainter,
        bookmarks: list[Bookmark],
        total_frames: int,
        width: int,
        viewport: TimelineViewport,
        dragging: bool,
        drag_source: int | None,
        drag_target: int | None,
    ) -> None:
        bookmarks_to_draw = list(bookmarks)
        if dragging and drag_source is not None and drag_target is not None:
            source_bm = next((b for b in bookmarks if b.frame == drag_source), None)
            bookmarks_to_draw = [b for b in bookmarks if b.frame != drag_source]
            bookmarks_to_draw.append(Bookmark(
                frame=drag_target,
                name=source_bm.name if source_bm else "",
                locked=source_bm.locked if source_bm else False,
            ))

        painter.setPen(Qt.PenStyle.NoPen)
        for bookmark in sorted(bookmarks_to_draw, key=lambda bm: bm.frame):
            x = viewport.frame_x(bookmark.frame, total_frames, width)
            marker_color = QColor(245, 139, 60, 240) if bookmark.locked else QColor(247, 193, 45, 240)
            painter.setBrush(marker_color)
            painter.drawPolygon(QPolygonF([
                QPointF(x - 6, 12),
                QPointF(x + 6, 12),
                QPointF(x, 22),
            ]))
            if bookmark.name:
                painter.setPen(QColor(237, 241, 244, 230))
                painter.drawText(
                    QRectF(x - 90, 0, 180, 12),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                    bookmark.name,
                )
                painter.setPen(Qt.PenStyle.NoPen)
