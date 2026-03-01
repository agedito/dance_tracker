from PySide6.QtCore import QPointF, Qt, QRectF, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QLineEdit, QWidget

from app.interface.layers import Segment
from app.interface.sequence_data import Bookmark
from ui.widgets.generic_widgets.context_menu import ContextMenuWidget
from ui.widgets.timeline_painter import TimelineTrackPainter
from ui.widgets.timeline_viewport import TimelineViewport
from utils.numbers import clamp


class _BookmarkEditor:
    """Inline QLineEdit for renaming bookmarks, embedded inside a parent QWidget."""

    def __init__(self, parent: QWidget, on_editing_finished) -> None:
        self._editor = QLineEdit(parent)
        self._editor.hide()
        self._editor.setPlaceholderText("Bookmark name")
        self._editor.editingFinished.connect(on_editing_finished)
        self._editing_frame: int | None = None

    @property
    def editing_frame(self) -> int | None:
        return self._editing_frame

    def start(self, frame: int, name: str, label_rect: QRectF) -> None:
        self._editing_frame = frame
        self._editor.setText(name)
        self._editor.setGeometry(label_rect.adjusted(0, 0, 0, 10).toRect())
        self._editor.show()
        self._editor.setFocus()
        self._editor.selectAll()

    def finish(self) -> tuple[int, str] | None:
        if self._editing_frame is None:
            return None
        frame = self._editing_frame
        self._editing_frame = None
        self._editor.hide()
        return frame, self._editor.text()

    def cancel(self) -> None:
        self._editing_frame = None
        self._editor.hide()

    def reposition(self, label_rect: QRectF) -> None:
        self._editor.setGeometry(label_rect.adjusted(0, 0, 0, 10).toRect())

    def update_for_bookmarks(self, bookmarks: list[Bookmark], name: str, label_rect: QRectF) -> None:
        if self._editing_frame is None:
            return
        if not any(b.frame == self._editing_frame for b in bookmarks):
            self.cancel()
            return
        self._editor.setText(name)
        self._editor.selectAll()
        self.reposition(label_rect)


class TimelineTrack(QWidget):
    frameChanged = Signal(int)
    viewportChanged = Signal(float, float)
    scrubStarted = Signal()
    scrubFinished = Signal()
    bookmarkRequested = Signal(int)
    bookmarkMoved = Signal(int, int)
    bookmarkRemoved = Signal(int)
    bookmarkNameChanged = Signal(int, str)
    bookmarkLockChanged = Signal(int, bool)

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
        self._viewport = TimelineViewport()
        self._editor = _BookmarkEditor(self, self._finish_bookmark_rename)
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.CrossCursor)

    # ── Viewport ─────────────────────────────────────────────────────

    def _emit_if_changed(self, changed: bool) -> None:
        if changed:
            self.viewportChanged.emit(self._viewport.view_start, self._viewport.view_span)

    def set_shared_viewport(self, start: float, span: float) -> None:
        self._viewport.set(start, span)
        self.update()

    # ── Public setters ───────────────────────────────────────────────

    def set_total_frames(self, total_frames: int) -> None:
        self.total_frames = max(1, total_frames)
        self.frame = clamp(self.frame, 0, self.total_frames - 1)
        self.bookmarks = [b for b in self.bookmarks if b.frame < self.total_frames]
        if self._editor.editing_frame is not None and self._editor.editing_frame >= self.total_frames:
            self._editor.cancel()
        self.loaded_flags = [False] * self.total_frames
        self._emit_if_changed(self._viewport.set(self._viewport.view_start, self._viewport.view_span))
        self.update()

    def set_frame(self, f: int) -> None:
        self.frame = clamp(f, 0, self.total_frames - 1)
        if self.total_frames > 1:
            norm_frame = self.frame / (self.total_frames - 1)
            if norm_frame < self._viewport.view_start:
                self._emit_if_changed(self._viewport.set(norm_frame, self._viewport.view_span))
            elif norm_frame > self._viewport.visible_end:
                self._emit_if_changed(
                    self._viewport.set(norm_frame - self._viewport.view_span, self._viewport.view_span)
                )
        self.update()

    def set_bookmarks(self, bookmarks: list[Bookmark]) -> None:
        by_frame = {
            clamp(b.frame, 0, self.total_frames - 1): Bookmark(
                frame=clamp(b.frame, 0, self.total_frames - 1),
                name=b.name.strip(),
                locked=b.locked,
            )
            for b in bookmarks
        }
        self.bookmarks = [by_frame[frame] for frame in sorted(by_frame)]
        editing = self._editor.editing_frame
        if editing is not None:
            self._editor.update_for_bookmarks(
                self.bookmarks,
                self._bookmark_name(editing),
                self._bookmark_label_rect(editing),
            )
        self.update()

    def set_loaded_flags(self, flags: list[bool]) -> None:
        if len(flags) != self.total_frames:
            self.loaded_flags = (flags + [False] * self.total_frames)[: self.total_frames]
        else:
            self.loaded_flags = list(flags)
        self.update()

    def set_frame_loaded(self, frame: int, loaded: bool) -> None:
        if 0 <= frame < self.total_frames:
            self.loaded_flags[frame] = loaded
            self.update()

    # ── Bookmark queries ─────────────────────────────────────────────

    def _bookmark_near_pos(self, x: float, threshold_px: int = 8) -> int | None:
        nearest: int | None = None
        nearest_dist: float | None = None
        for bookmark in self.bookmarks:
            marker_x = self._viewport.frame_x(bookmark.frame, self.total_frames, self.width())
            dist = abs(marker_x - x)
            if dist > threshold_px:
                continue
            if nearest_dist is None or dist < nearest_dist:
                nearest_dist = dist
                nearest = bookmark.frame
        return nearest

    def _bookmark_name(self, frame: int) -> str:
        return next((b.name for b in self.bookmarks if b.frame == frame), "")

    def _is_bookmark_locked(self, frame: int) -> bool:
        return next((b.locked for b in self.bookmarks if b.frame == frame), False)

    def _bookmark_label_rect(self, frame: int) -> QRectF:
        x = self._viewport.frame_x(frame, self.total_frames, self.width())
        return QRectF(x - 90, 0, 180, 12)

    def _bookmark_at_position(self, x: float, y: float) -> int | None:
        for bookmark in self.bookmarks:
            if self._bookmark_label_rect(bookmark.frame).adjusted(-4, -2, 4, 2).contains(QPointF(x, y)):
                return bookmark.frame
        return self._bookmark_near_pos(x)

    # ── Mouse events ─────────────────────────────────────────────────

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.MiddleButton:
            self._viewport.start_pan(ev.position().x())
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            ev.accept()
            return

        if ev.button() == Qt.MouseButton.RightButton:
            self._show_bookmark_context_menu(ev)
            return

        if ev.button() != Qt.MouseButton.LeftButton:
            return

        if self._editor.editing_frame is not None:
            self._finish_bookmark_rename()

        bookmark = self._bookmark_near_pos(ev.position().x())
        if bookmark is not None:
            if self._is_bookmark_locked(bookmark):
                return
            self._dragging_bookmark = True
            self._drag_source_bookmark = bookmark
            self._drag_bookmark_frame = bookmark
            self.update()
            return

        self.scrubStarted.emit()
        self.frameChanged.emit(
            self._viewport.frame_from_pos(ev.position().x(), self.width(), self.total_frames)
        )

    def mouseMoveEvent(self, ev):
        if self._viewport.panning:
            self._emit_if_changed(self._viewport.pan_to(ev.position().x(), self.width()))
            self.update()
            ev.accept()
            return

        if not (ev.buttons() & Qt.MouseButton.LeftButton):
            return

        if self._dragging_bookmark:
            self._drag_bookmark_frame = self._viewport.frame_from_pos(
                ev.position().x(), self.width(), self.total_frames
            )
            self.update()
            return

        self.frameChanged.emit(
            self._viewport.frame_from_pos(ev.position().x(), self.width(), self.total_frames)
        )

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.MiddleButton and self._viewport.panning:
            self._viewport.stop_pan()
            self.setCursor(Qt.CursorShape.CrossCursor)
            ev.accept()
            return

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

    def mouseDoubleClickEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            bookmark = self._bookmark_at_position(ev.position().x(), ev.position().y())
            if bookmark is not None and not self._is_bookmark_locked(bookmark):
                self._start_bookmark_rename(bookmark)
                ev.accept()
                return
        super().mouseDoubleClickEvent(ev)

    def wheelEvent(self, ev):
        delta_y = ev.angleDelta().y()
        if delta_y == 0:
            ev.ignore()
            return
        self._emit_if_changed(self._viewport.zoom_at(ev.position().x(), self.width(), zoom_in=delta_y > 0))
        self.update()
        ev.accept()

    # ── Context menu ─────────────────────────────────────────────────

    def _show_bookmark_context_menu(self, ev) -> None:
        clicked_frame = self._viewport.frame_from_pos(ev.position().x(), self.width(), self.total_frames)
        bookmark = self._bookmark_near_pos(ev.position().x())

        menu = ContextMenuWidget(self)

        if bookmark is None:
            add_action = menu.addAction("Add bookmark")
            menu.setActiveAction(add_action)
            if menu.exec(ev.globalPosition().toPoint()) == add_action:
                self.bookmarkRequested.emit(clicked_frame)
            return

        if self._is_bookmark_locked(bookmark):
            unlock_action = menu.addAction("Unlock bookmark")
            menu.setActiveAction(unlock_action)
            if menu.exec(ev.globalPosition().toPoint()) == unlock_action:
                if self._editor.editing_frame == bookmark:
                    self._editor.cancel()
                self.bookmarkLockChanged.emit(bookmark, False)
            return

        edit_name_action = menu.addAction("Edit bookmark name")
        delete_action = menu.addAction("Delete bookmark")
        menu.addSeparator()
        lock_action = menu.addAction("Lock bookmark")
        menu.setActiveAction(edit_name_action)

        chosen = menu.exec(ev.globalPosition().toPoint())
        if chosen == edit_name_action:
            self._start_bookmark_rename(bookmark)
        elif chosen == delete_action:
            if self._editor.editing_frame == bookmark:
                self._editor.cancel()
            self.bookmarkRemoved.emit(bookmark)
        elif chosen == lock_action:
            if self._editor.editing_frame == bookmark:
                self._editor.cancel()
            self.bookmarkLockChanged.emit(bookmark, True)

    # ── Bookmark editor ──────────────────────────────────────────────

    def resizeEvent(self, ev):
        editing = self._editor.editing_frame
        if editing is not None:
            self._editor.reposition(self._bookmark_label_rect(editing))
        super().resizeEvent(ev)

    def _start_bookmark_rename(self, frame: int) -> None:
        self._editor.start(frame, self._bookmark_name(frame), self._bookmark_label_rect(frame))

    def _finish_bookmark_rename(self) -> None:
        result = self._editor.finish()
        if result is not None:
            frame, name = result
            self.bookmarkNameChanged.emit(frame, name)

    # ── Paint ────────────────────────────────────────────────────────

    def paintEvent(self, _ev):
        p = QPainter(self)
        TimelineTrackPainter.paint(
            p,
            self.width(),
            self.height(),
            self.total_frames,
            self.frame,
            self._viewport,
            self.segments,
            self.loaded_flags,
            self.bookmarks,
            self._dragging_bookmark,
            self._drag_source_bookmark,
            self._drag_bookmark_frame,
        )
        p.end()
