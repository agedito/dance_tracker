from PySide6.QtCore import QPointF, Qt, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QInputDialog, QMenu, QWidget

from app.interface.sequence_data import Bookmark
from app.track_app.frame_state.layers import Segment
from utils.numbers import clamp


def status_color(t: str) -> QColor:
    _ = t
    return QColor(0, 0, 0, 220)


class TimelineTrack(QWidget):
    frameChanged = Signal(int)
    scrubStarted = Signal()
    scrubFinished = Signal()
    bookmarkRequested = Signal(int)
    bookmarkMoved = Signal(int, int)
    bookmarkRemoved = Signal(int)
    bookmarkNameChanged = Signal(int, str)

    def __init__(self, total_frames: int, segments: list[Segment], parent=None):
        super().__init__(parent)
        self.total_frames = max(1, total_frames)
        self.segments = segments
        self.frame = 0
        self.loaded_flags = [False] * self.total_frames
        self.bookmarks: list[Bookmark] = []
        self._dragging_bookmark = False
        self._drag_source_bookmark: int | None = None
        self._drag_bookmark_frame: int | None = None
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _frame_from_pos(self, x: float) -> int:
        norm_x = clamp(int(x), 0, self.width())
        return int(round((norm_x / max(1, self.width())) * (self.total_frames - 1)))

    def _frame_x(self, frame: int) -> int:
        return int((clamp(frame, 0, self.total_frames - 1) / max(1, self.total_frames - 1)) * self.width())

    def _bookmark_near_pos(self, x: float, threshold_px: int = 8) -> int | None:
        if not self.bookmarks:
            return None

        nearest: int | None = None
        nearest_distance: float | None = None
        for bookmark in self.bookmarks:
            marker_x = self._frame_x(bookmark.frame)
            distance = abs(marker_x - x)
            if distance > threshold_px:
                continue
            if nearest_distance is None or distance < nearest_distance:
                nearest_distance = distance
                nearest = bookmark.frame
        return nearest

    def _bookmark_name(self, frame: int) -> str:
        for bookmark in self.bookmarks:
            if bookmark.frame == frame:
                return bookmark.name
        return ""

    def set_total_frames(self, total_frames: int):
        self.total_frames = max(1, total_frames)
        self.frame = clamp(self.frame, 0, self.total_frames - 1)
        self.bookmarks = [bookmark for bookmark in self.bookmarks if bookmark.frame < self.total_frames]
        self.loaded_flags = [False] * self.total_frames
        self.update()

    def set_frame(self, f: int):
        self.frame = clamp(f, 0, self.total_frames - 1)
        self.update()

    def set_bookmarks(self, bookmarks: list[Bookmark]):
        by_frame = {
            clamp(bookmark.frame, 0, self.total_frames - 1): bookmark.name.strip()
            for bookmark in bookmarks
        }
        self.bookmarks = [
            Bookmark(frame=frame, name=name)
            for frame, name in sorted(by_frame.items())
        ]
        self.update()

    def set_loaded_flags(self, flags: list[bool]):
        if len(flags) != self.total_frames:
            self.loaded_flags = (flags + [False] * self.total_frames)[:self.total_frames]
        else:
            self.loaded_flags = list(flags)
        self.update()

    def set_frame_loaded(self, frame: int, loaded: bool):
        if frame < 0 or frame >= self.total_frames:
            return
        self.loaded_flags[frame] = loaded
        self.update()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.MiddleButton:
            self.bookmarkRequested.emit(self._frame_from_pos(ev.position().x()))
            return

        if ev.button() == Qt.MouseButton.RightButton:
            self._show_bookmark_context_menu(ev)
            return

        if ev.button() != Qt.MouseButton.LeftButton:
            return

        bookmark = self._bookmark_near_pos(ev.position().x())
        if bookmark is not None:
            self._dragging_bookmark = True
            self._drag_source_bookmark = bookmark
            self._drag_bookmark_frame = bookmark
            self.update()
            return

        self.scrubStarted.emit()
        self.frameChanged.emit(self._frame_from_pos(ev.position().x()))

    def mouseMoveEvent(self, ev):
        if not (ev.buttons() & Qt.MouseButton.LeftButton):
            return

        if self._dragging_bookmark:
            self._drag_bookmark_frame = self._frame_from_pos(ev.position().x())
            self.update()
            return

        self.frameChanged.emit(self._frame_from_pos(ev.position().x()))

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton and self._dragging_bookmark:
            source = self._drag_source_bookmark
            target = self._drag_bookmark_frame
            self._dragging_bookmark = False
            self._drag_source_bookmark = None
            self._drag_bookmark_frame = None
            self.update()
            if source is not None and target is not None and source != target:
                self.bookmarkMoved.emit(source, target)
            super().mouseReleaseEvent(ev)
            return

        if ev.button() == Qt.MouseButton.LeftButton:
            self.scrubFinished.emit()
        super().mouseReleaseEvent(ev)

    def _prompt_bookmark_name(self, current_name: str) -> tuple[str, bool]:
        dialog = QInputDialog(self)
        dialog.setInputMode(QInputDialog.InputMode.TextInput)
        dialog.setWindowTitle("Bookmark name")
        dialog.setLabelText("Name:")
        dialog.setTextValue(current_name)
        dialog.setOkButtonText("OK")
        dialog.setCancelButtonText("Cancel")

        flags = dialog.windowFlags()
        flags |= Qt.WindowType.Dialog
        flags |= Qt.WindowType.CustomizeWindowHint
        flags |= Qt.WindowType.WindowTitleHint
        flags |= Qt.WindowType.WindowCloseButtonHint
        flags &= ~Qt.WindowType.WindowMinimizeButtonHint
        flags &= ~Qt.WindowType.WindowMaximizeButtonHint
        flags &= ~Qt.WindowType.WindowContextHelpButtonHint
        dialog.setWindowFlags(flags)

        accepted = dialog.exec() == QInputDialog.DialogCode.Accepted
        return dialog.textValue(), accepted

    def _show_bookmark_context_menu(self, ev) -> None:
        clicked_frame = self._frame_from_pos(ev.position().x())
        bookmark = self._bookmark_near_pos(ev.position().x())

        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #1A1F23;
                border: 1px solid #2B343B;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3A3F45;
            }
            QMenu::separator {
                height: 1px;
                background: #4B525A;
                margin: 6px 4px;
            }
            """
        )
        add_action = None
        edit_name_action = None
        delete_action = None

        if bookmark is None:
            add_action = menu.addAction("Add bookmark")
        else:
            edit_name_action = menu.addAction("Edit bookmark name")
            delete_action = menu.addAction("Delete bookmark")

        chosen_action = menu.exec(ev.globalPosition().toPoint())
        if chosen_action == add_action:
            self.bookmarkRequested.emit(clicked_frame)
            return

        if chosen_action == edit_name_action:
            current_name = self._bookmark_name(bookmark)
            name, ok = self._prompt_bookmark_name(current_name)
            if ok:
                self.bookmarkNameChanged.emit(bookmark, name)
        elif chosen_action == delete_action:
            self.bookmarkRemoved.emit(bookmark)

    def paintEvent(self, ev):
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        p.setBrush(QColor(12, 15, 18))
        p.setPen(QPen(QColor(43, 52, 59), 1))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 9, 9)

        for s in self.segments:
            left = int((s.a / self.total_frames) * w)
            right = int((s.b / self.total_frames) * w)
            seg_w = max(1, right - left)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(status_color(s.t))
            p.drawRect(QRectF(left, 12, seg_w, h - 16))

        self._draw_loaded_indicator(p, w, h)
        self._draw_bookmarks(p)

        xph = int((self.frame / max(1, self.total_frames - 1)) * w)
        p.setPen(QPen(QColor(255, 80, 80, 240), 2))
        p.drawLine(xph, -4, xph, h + 4)
        p.end()

    def _draw_loaded_indicator(self, painter: QPainter, w: int, h: int):
        bar_h = 3
        y = h - bar_h - 1
        painter.setPen(Qt.PenStyle.NoPen)

        if w <= 1:
            color = QColor(42, 160, 88, 240) if self.loaded_flags and self.loaded_flags[0] else QColor(95, 98, 102, 200)
            painter.setBrush(color)
            painter.drawRect(QRectF(1, y, max(1, w - 2), bar_h))
            return

        for x in range(1, w - 1):
            frame = int((x / max(1, w - 1)) * (self.total_frames - 1))
            loaded = self.loaded_flags[frame] if frame < len(self.loaded_flags) else False
            color = QColor(42, 160, 88, 240) if loaded else QColor(95, 98, 102, 200)
            painter.setBrush(color)
            painter.drawRect(QRectF(x, y, 1, bar_h))

    def _draw_bookmarks(self, painter: QPainter):
        bookmarks_to_draw = list(self.bookmarks)
        if self._dragging_bookmark and self._drag_bookmark_frame is not None:
            bookmarks_to_draw = [
                bookmark
                for bookmark in self.bookmarks
                if bookmark.frame != self._drag_source_bookmark
            ]
            bookmarks_to_draw.append(
                Bookmark(frame=self._drag_bookmark_frame, name=self._bookmark_name(self._drag_source_bookmark or -1))
            )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(247, 193, 45, 240))

        for bookmark in sorted(bookmarks_to_draw, key=lambda item: item.frame):
            x = self._frame_x(bookmark.frame)
            marker = QPolygonF([
                QPointF(x - 6, 12),
                QPointF(x + 6, 12),
                QPointF(x, 22),
            ])
            painter.drawPolygon(marker)

            if bookmark.name:
                text_rect = QRectF(x - 90, 0, 180, 12)
                painter.setPen(QColor(237, 241, 244, 230))
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, bookmark.name)
                painter.setPen(Qt.PenStyle.NoPen)
