import sys

from PySide6.QtWidgets import QApplication

from app.interface.application import DanceTrackerPort
from app.interface.event_bus import EventBus
from ui.config import Config
from ui.window.main_window import MainWindow


class GraphicApp:
    def __init__(self, app: DanceTrackerPort):
        self._app = app

    def launch(self, cfg: Config, bus: EventBus):
        qt_app = QApplication(sys.argv)
        wnd = MainWindow(cfg, self._app, bus)
        bus.connect(wnd)

        sys.exit(qt_app.exec())
