import sys

from PySide6.QtWidgets import QApplication

from app.main_app import DanceTrackerApp
from ui.config import Config
from ui.window.main_window import MainWindow


class GraphicApp:
    def __init__(self, app: DanceTrackerApp):
        self.app = app

    def launch(self, cfg: Config):
        main_app = QApplication(sys.argv)
        MainWindow(cfg, self.app)
        sys.exit(main_app.exec())
