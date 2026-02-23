import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app_logic import ReviewState, default_layers
from widgets.thumbnail import ThumbnailWidget
from widgets.timeline import TimelineTrack
from widgets.viewer import ViewerWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = ReviewState(total_frames=1200, fps=30, layers=default_layers())

        self.timer = QTimer(self)
        self.timer.setInterval(int(1000 / self.state.fps))
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

        self.viewer = ViewerWidget(self.state.total_frames)
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
        btn_back.clicked.connect(lambda: self.set_frame(self.state.cur_frame - 1))
        btn_fwd.clicked.connect(lambda: self.set_frame(self.state.cur_frame + 1))
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

        for layer in self.state.layers:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(10)
            name = QLabel(layer.name, objectName="LayerName")
            name.setFixedWidth(160)
            track = TimelineTrack(self.state.total_frames, layer.segments)
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
        grid.addWidget(a, 0, 0)
        grid.addWidget(self.stat_total, 0, 1)
        grid.addWidget(b, 1, 0)
        grid.addWidget(self.stat_err, 1, 1)
        grid.addWidget(c, 2, 0)
        grid.addWidget(self.stat_cur, 2, 1)
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

    def set_frame(self, frame: int):
        self.state.set_frame(frame)
        self.viewer.set_frame(self.state.cur_frame)
        for tr in self.track_widgets:
            tr.set_frame(self.state.cur_frame)
        self.viewer_info.setText(f"Frame: {self.state.cur_frame}")
        self.time_info.setText(
            f"Total frames: {self.state.total_frames} · Error frames: {len(self.state.error_frames)}"
        )
        self.stat_total.setText(str(self.state.total_frames))
        self.stat_err.setText(str(len(self.state.error_frames)))
        self.stat_cur.setText(str(self.state.cur_frame))
        self.frame_big.setText(str(self.state.cur_frame))

    def play(self):
        if self.state.playing:
            return
        self.state.playing = True
        self.timer.start()

    def pause(self):
        self.state.playing = False
        self.timer.stop()

    def _tick(self):
        advanced = self.state.advance_if_playing()
        if not advanced and not self.state.playing:
            self.timer.stop()
            return
        self.set_frame(self.state.cur_frame)

    def next_error(self):
        updated = self.state.next_error_frame()
        if updated is not None:
            self.set_frame(updated)

    def prev_error(self):
        updated = self.state.prev_error_frame()
        if updated is not None:
            self.set_frame(updated)

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
