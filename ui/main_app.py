import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.interface.application import DanceTrackerPort
from app.interface.event_bus import EventBus
from ui.config import Config
from ui.window.main_window import MainWindow
from ui.window.sections.preferences_manager import PreferencesManager


class GraphicApp:
    def __init__(self, app: DanceTrackerPort):
        self._app = app

    def launch(self, cfg: Config, bus: EventBus, prefs: PreferencesManager):
        qt_app = QApplication(sys.argv)
        wnd = MainWindow(cfg, self._app, bus, prefs)
        bus.connect(wnd)

        self._app.sequences.refresh()
        last_folder = self._app.sequences.last_opened_folder()
        if isinstance(last_folder, str) and Path(last_folder).expanduser().is_dir():
            self._app.sequences.load(last_folder)

        sys.exit(qt_app.exec())
