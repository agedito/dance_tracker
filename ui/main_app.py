import sys

from PySide6.QtWidgets import QApplication

from app.interface.application import DanceTrackerPort
from app.track_app.main_app import DanceTrackerApp
from ui.config import Config
from ui.window.main_window import MainWindow


class GraphicApp:
    def __init__(self, cfg: Config, old_app: DanceTrackerApp, app: DanceTrackerPort):
        self._qt_app = QApplication(sys.argv)
        self._wnd = MainWindow(cfg, old_app, app)

    def launch(self):
        sys.exit(self._qt_app.exec())
