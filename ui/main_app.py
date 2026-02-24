import sys

from PySide6.QtWidgets import QApplication

from app.interface.application import DanceTrackerPort
from app.interface.event_bus import EventBus
from app.track_app.main_app import DanceTrackerApp
from ui.config import Config
from ui.window.main_window import MainWindow


class GraphicApp:
    def __init__(self, old_app: DanceTrackerApp, app: DanceTrackerPort):
        self._old_app = old_app
        self._app = app

    def launch(self, cfg: Config, bus: EventBus):
        qt_app = QApplication(sys.argv)
        wnd = MainWindow(cfg, self._old_app, self._app)
        bus.connect(wnd)

        sys.exit(qt_app.exec())
