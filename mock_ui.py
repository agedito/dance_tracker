import sys
from dataclasses import dataclass
from typing import List

from PySide6.QtCore import Qt, QTimer, QRectF, Signal, QSize
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QGridLayout, QFrame, QSizePolicy, QScrollArea
)


@dataclass(frozen=True)
class Segment:
    a: int
    b: int
    t: str  # "ok" | "warn" | "err"


@dataclass(frozen=True)
class Layer:
    name: str
    segments: List[Segment]


def clamp(n: int, a: int, b: int) -> int:
    return max(a, min(b, n))


def status_color(t: str) -> QColor:
    if t == "ok":
        return QColor(46, 204, 113, 190)
    if t == "warn":
        return QColor(241, 196, 15, 200)
    if t == "err":
        return QColor(231, 76, 60, 220)
    return QColor(120, 120, 120, 180)


class ViewerWidget(QWidget):
    def __init__(self, total_frames: int, parent=None):
        super().__init__(parent)
        self.total_frames = total_frames
        self.frame = 0
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_frame(self, f: int):
        self.frame = clamp(f, 0, self.total_frames - 1)
        self.update()

    def paintEvent(self, ev):
        import math
        w, h = self.width(), self.height()
        f = self.frame
        t = f / max(1, (self.total_frames - 1))

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor(12, 14, 16))

        g = QLinearGradient(0, 0, w, h)
        g.setColorAt(0.0, QColor(20, 45, 25, 240))
        g.setColorAt(1.0, QColor(80, 70, 20, 180))
        p.fillRect(self.rect(), QBrush(g))

        for i in range(18):
            px = int((0.5 + 0.5 * math.sin((i * 999) + t * 8.0)) * w)
            py = int((0.5 + 0.5 * math.cos((i * 777) + t * 6.0)) * h)
            r = int((0.05 + (i % 5) * 0.02) * min(w, h))
            rg = QRadialGradient(px, py, r)
            alpha = 18 + (i % 4) * 6
            rg.setColorAt(0.0, QColor(255, 255, 255, alpha))
            rg.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setBrush(QBrush(rg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(px - r, py - r, 2 * r, 2 * r)

        vg = QRadialGradient(int(w * 0.5), int(h * 0.55), int(min(w, h) * 0.75))
        vg.setColorAt(0.0, QColor(0, 0, 0, 0))
        vg.setColorAt(1.0, QColor(0, 0, 0, 160))
        p.fillRect(self.rect(), QBrush(vg))

        p.setPen(QColor(255, 255, 255, 190))
        p.setFont(QFont("Segoe UI", max(10, int(h * 0.05)), QFont.Weight.DemiBold))
        p.drawText(20, int(h * 0.15), f"Frame {f}")

        p.setFont(QFont("Segoe UI", max(9, int(h * 0.04)), QFont.Weight.DemiBold))
        p.setPen(QColor(255, 255, 255, 170))
        wm_text = "NATIONAL GEOGRAPHIC"
        text_w = p.fontMetrics().horizontalAdvance(wm_text)
        x = w - text_w - 20
        y = h - 18
        p.setPen(QPen(QColor(255, 210, 74), 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(x - 28, y - 14, 18, 18)
        p.setPen(QColor(255, 255, 255, 170))
        p.drawText(x, y, wm_text)

        xph = int((f / max(1, self.total_frames - 1)) * w)
        p.setPen(QPen(QColor(255, 80, 80, 230), 2))
        p.drawLine(xph, 0, xph, h)
        p.end()


class ThumbnailWidget(QWidget):
    def __init__(self, label: str, seed: int = 1, parent=None):
        super().__init__(parent)
        self.label = label
        self.seed = seed
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, ev):
        import math
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        p.fillRect(self.rect(), QColor(12, 15, 18))
        g = QLinearGradient(0, 0, w, h)
        g.setColorAt(0.0, QColor(40 + (self.seed % 50), 70 + (self.seed % 80), 40 + (self.seed % 60), 235))
        g.setColorAt(1.0, QColor(110 + (self.seed % 60), 95 + (self.seed % 40), 30 + (self.seed % 30), 180))
        p.fillRect(self.rect(), QBrush(g))

        for i in range(10):
            px = int((0.5 + 0.5 * math.sin((self.seed + i) * 3.1)) * w)
            py = int((0.5 + 0.5 * math.cos((self.seed + i) * 2.3)) * h)
            r = int((0.12 + (i % 4) * 0.05) * min(w, h))
            rg = QRadialGradient(px, py, r)
            alpha = 16 + (i % 3) * 12
            rg.setColorAt(0.0, QColor(255, 255, 255, alpha))
            rg.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setBrush(QBrush(rg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(px - r, py - r, 2 * r, 2 * r)

        p.setPen(QPen(QColor(255, 80, 80, 210), max(2, int(min(w, h) * 0.05))))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(int(w * 0.18), int(h * 0.65), int(w * 0.82), int(h * 0.55))

        p.setPen(QColor(255, 255, 255, 190))
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        p.drawText(10, 18, self.label)

        p.setPen(QPen(QColor(43, 52, 59), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 8, 8)
        p.end()


class TimelineTrack(QWidget):
    frameChanged = Signal(int)

    def __init__(self, total_frames: int, segments: List[Segment], parent=None):
        super().__init__(parent)
        self.total_frames = total_frames
        self.segments = segments
        self.frame = 0
        self.setFixedHeight(20)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_frame(self, f: int):
        self.frame = clamp(f, 0, self.total_frames - 1)
        self.update()

    def mousePressEvent(self, ev):
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        x = clamp(ev.position().x(), 0, self.width())
        f = int(round((x / max(1, self.width())) * (self.total_frames - 1)))
        self.frameChanged.emit(f)

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
            p.drawRect(QRectF(left, 1, seg_w, h - 2))

        xph = int((self.frame / max(1, self.total_frames - 1)) * w)
        p.setPen(QPen(QColor(255, 80, 80, 240), 2))
        p.drawLine(xph, -4, xph, h + 4)
        p.end()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.total_frames = 1200
        self.fps = 30
        self.layers = [
            Layer("Layer 0: Master Video", [
                Segment(0, 220, "ok"), Segment(220, 420, "warn"), Segment(420, 520, "ok"),
                Segment(520, 560, "err"), Segment(560, 980, "warn"), Segment(980, 1200, "ok"),
            ]),
            Layer("Layer 1: Color Grade", [
                Segment(0, 120, "ok"), Segment(120, 240, "warn"), Segment(240, 760, "ok"),
                Segment(760, 820, "err"), Segment(820, 1200, "ok"),
            ]),
            Layer("Layer 2: Object Mask", [
                Segment(0, 430, "ok"), Segment(430, 470, "err"), Segment(470, 900, "ok"),
                Segment(900, 980, "warn"), Segment(980, 1200, "ok"),
            ]),
        ]
        self.error_frames = self._compute_error_frames()
        self.cur_frame = 0
        self.playing = False

        self.timer = QTimer(self)
        self.timer.setInterval(int(1000 / self.fps))
        self.timer.timeout.connect(self._tick)

        self.setWindowTitle("Frame Review UI (PySide6 mock)")
        self.resize(1200, 780)

        root = QWidget()
        self.setCentralWidget(root)
        root.setStyleSheet(self._qss())

        outer = QVBoxLayout(root)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(10)

        outer.addWidget(self._topbar())

        main = QHBoxLayout()
        main.setSpacing(10)
        outer.addLayout(main, 3)

        self.viewer_block = self._viewer_block()
        self.right_panel = self._right_panel()

        main.addWidget(self.viewer_block, 3)
        main.addWidget(self.right_panel, 2)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        outer.addLayout(bottom, 2)

        self.timeline_panel = self._timeline_panel()
        self.status_panel = self._status_panel()

        bottom.addWidget(self.timeline_panel, 4)
        bottom.addWidget(self.status_panel, 2)

        self.set_frame(0)

    def _topbar(self):
        w = QWidget(objectName="TopBar")
        l = QHBoxLayout(w)
        l.setContentsMargins(12, 10, 12, 10)
        title = QLabel("MAIN VIEWER", objectName="TopTitle")
        hint = QLabel("Mock UI · Frames fijos · Click en timelines", objectName="TopHint")
        l.addWidget(title)
        l.addStretch(1)
        l.addWidget(hint)
        return w

    def _viewer_block(self):
        block = QFrame(objectName="Panel")
        v = QVBoxLayout(block)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        header = QWidget(objectName="PanelHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.addWidget(QLabel("Viewer"))
        hl.addStretch(1)
        self.viewer_info = QLabel("Frame: 0", objectName="Muted")
        hl.addWidget(self.viewer_info)
        v.addWidget(header)

        self.viewer = ViewerWidget(self.total_frames)
        v.addWidget(self.viewer, 1)

        footer = QWidget(objectName="PanelFooter")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(10, 10, 10, 10)
        fl.setSpacing(8)

        btn_play = QPushButton("PLAY", objectName="PrimaryButton")
        btn_pause = QPushButton("PAUSE")
        btn_back = QPushButton("STEP BACK")
        btn_fwd = QPushButton("STEP FORWARD")
        btn_next = QPushButton("NEXT ERROR")

        btn_play.clicked.connect(self.play)
        btn_pause.clicked.connect(self.pause)
        btn_back.clicked.connect(lambda: self.set_frame(self.cur_frame - 1))
        btn_fwd.clicked.connect(lambda: self.set_frame(self.cur_frame + 1))
        btn_next.clicked.connect(self.next_error)

        fl.addWidget(btn_play)
        fl.addWidget(btn_pause)
        fl.addWidget(btn_back)
        fl.addWidget(btn_fwd)
        fl.addWidget(btn_next)
        fl.addStretch(1)

        v.addWidget(footer)
        return block

    def _right_panel(self):
        panel = QFrame(objectName="Panel")
        v = QVBoxLayout(panel)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(10)

        v.addWidget(QLabel("LAYER VIEWERS", objectName="SectionTitle"))
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.addWidget(self._thumb("Layer 1: Color Grade", 10), 0, 0)
        grid.addWidget(self._thumb("Layer 1: Output", 17), 0, 1)
        v.addLayout(grid)

        v.addWidget(QLabel("LAYER 2: OBJECT MASK", objectName="SectionTitle"))
        grid2 = QGridLayout()
        grid2.setSpacing(8)
        grid2.addWidget(self._thumb("Layer 2: Mask", 24), 0, 0)
        grid2.addWidget(self._thumb("Layer 2: Overlay", 31), 0, 1)
        v.addLayout(grid2)

        v.addStretch(1)
        v.addWidget(QLabel("Mock: thumbnails procedurales.", objectName="FooterNote"))
        return panel

    def _thumb(self, label: str, seed: int):
        f = QFrame(objectName="ThumbFrame")
        l = QVBoxLayout(f)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(ThumbnailWidget(label, seed))
        return f

    def _timeline_panel(self):
        panel = QFrame(objectName="Panel")
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        header = QWidget(objectName="PanelHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.addWidget(QLabel("MASTER TIMELINE"))
        hl.addStretch(1)
        self.time_info = QLabel("", objectName="Muted")
        hl.addWidget(self.time_info)
        v.addWidget(header)

        scroll = QScrollArea(objectName="ScrollArea")
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.track_widgets = []

        lay = QVBoxLayout(content)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        for layer in self.layers:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(10)
            name = QLabel(layer.name, objectName="LayerName")
            name.setFixedWidth(160)
            track = TimelineTrack(self.total_frames, layer.segments)
            track.frameChanged.connect(self.set_frame)
            self.track_widgets.append(track)
            rl.addWidget(name)
            rl.addWidget(track, 1)
            lay.addWidget(row)

        lay.addStretch(1)
        scroll.setWidget(content)
        v.addWidget(scroll, 1)
        return panel

    def _status_panel(self):
        panel = QFrame(objectName="Panel")
        v = QVBoxLayout(panel)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(12)

        v.addWidget(QLabel("STATUS BAR", objectName="SectionTitle"))
        self.stat_total = QLabel("-", objectName="BoldValue")
        self.stat_err = QLabel("-", objectName="BoldValue")
        self.stat_cur = QLabel("-", objectName="BoldValue")

        grid = QGridLayout()
        grid.setSpacing(6)
        a = QLabel("Total frames", objectName="Muted")
        b = QLabel("Error frames", objectName="Muted")
        c = QLabel("Current frame", objectName="Muted")
        grid.addWidget(a, 0, 0); grid.addWidget(self.stat_total, 0, 1)
        grid.addWidget(b, 1, 0); grid.addWidget(self.stat_err, 1, 1)
        grid.addWidget(c, 2, 0); grid.addWidget(self.stat_cur, 2, 1)
        v.addLayout(grid)

        nav = QWidget()
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(0, 0, 0, 0)
        nl.setSpacing(8)
        prev_btn = QPushButton("PREVIOUS ERROR")
        next_btn = QPushButton("NEXT ERROR")
        prev_btn.clicked.connect(self.prev_error)
        next_btn.clicked.connect(self.next_error)
        nl.addWidget(prev_btn)
        nl.addWidget(next_btn)
        v.addWidget(QLabel("FRAME NAVIGATOR", objectName="SectionTitle"))
        v.addWidget(nav)

        v.addWidget(QLabel("FRAME", objectName="Muted"))
        self.frame_big = QLabel("0", objectName="FrameBig")
        v.addWidget(self.frame_big)

        v.addStretch(1)
        return panel

    def set_frame(self, f: int):
        self.cur_frame = clamp(f, 0, self.total_frames - 1)
        self.viewer.set_frame(self.cur_frame)
        for tr in self.track_widgets:
            tr.set_frame(self.cur_frame)
        self.viewer_info.setText(f"Frame: {self.cur_frame}")
        self.time_info.setText(f"Total frames: {self.total_frames} · Error frames: {len(self.error_frames)}")
        self.stat_total.setText(str(self.total_frames))
        self.stat_err.setText(str(len(self.error_frames)))
        self.stat_cur.setText(str(self.cur_frame))
        self.frame_big.setText(str(self.cur_frame))

    def play(self):
        if self.playing:
            return
        self.playing = True
        self.timer.start()

    def pause(self):
        self.playing = False
        self.timer.stop()

    def _tick(self):
        if not self.playing:
            return
        if self.cur_frame >= self.total_frames - 1:
            self.pause()
            return
        self.set_frame(self.cur_frame + 1)

    def next_error(self):
        for f in self.error_frames:
            if f > self.cur_frame:
                self.set_frame(f)
                return

    def prev_error(self):
        for f in reversed(self.error_frames):
            if f < self.cur_frame:
                self.set_frame(f)
                return

    def _compute_error_frames(self):
        s = set()
        for L in self.layers:
            for seg in L.segments:
                if seg.t == "err":
                    for f in range(seg.a, seg.b):
                        s.add(f)
        return sorted(s)

    def _qss(self):
        return """
        QWidget { background: #121416; color: #E7EDF2; font-family: Segoe UI, Arial; font-size: 12px; }
        #TopBar { background: #0F1113; border: 1px solid #2B343B; border-radius: 10px; }
        #TopTitle { font-weight: 700; letter-spacing: 0.5px; }
        #TopHint { color: #A7B3BD; }

        QFrame#Panel { background: #1A1F23; border: 1px solid #2B343B; border-radius: 10px; }
        QWidget#PanelHeader {
            background: #161B1F; border-bottom: 1px solid #2B343B;
            border-top-left-radius: 10px; border-top-right-radius: 10px;
        }
        QWidget#PanelFooter {
            background: #14181C; border-top: 1px solid #2B343B;
            border-bottom-left-radius: 10px; border-bottom-right-radius: 10px;
        }

        QLabel#Muted { color: #A7B3BD; }
        QLabel#SectionTitle { color: #A7B3BD; font-weight: 700; letter-spacing: 0.3px; }
        QLabel#LayerName { color: #A7B3BD; }
        QLabel#BoldValue { color: #E7EDF2; font-weight: 700; }
        QLabel#FrameBig { font-size: 20px; font-weight: 800; }
        QLabel#FooterNote { color: rgba(255,255,255,0.55); font-size: 11px; }

        QPushButton {
            background: #2A3238; border: 1px solid #2B343B;
            padding: 8px 10px; border-radius: 8px;
        }
        QPushButton:hover { background: #344049; }
        QPushButton#PrimaryButton { border: 1px solid rgba(122,162,255,110); }

        QScrollArea#ScrollArea { border: none; background: transparent; }
        QScrollArea#ScrollArea QWidget { background: transparent; }

        QFrame#ThumbFrame { background: #0C0F12; border: 1px solid #2B343B; border-radius: 10px; }
        """


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()