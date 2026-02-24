import sys

from PySide6.QtWidgets import QApplication

from app.interface.event_bus import EventBus
from app.track_app.adapter import AppAdapter
from app.track_app.config import Config as AppConfig
from app.track_app.main_app import DanceTrackerApp
from ui.config import Config as UiConfig
from ui.window.main_window import MainWindow


def launch():
    # Dance tracker app
    app_cfg = AppConfig()
    app = DanceTrackerApp(app_cfg)

    # create event buses
    events = EventBus()
    adapter = AppAdapter(app, events)

    # Graphic user interface
    ui_cfg = UiConfig()
    qt_app = QApplication(sys.argv)
    window = MainWindow(ui_cfg, app, adapter)

    events.connect(window)
    sys.exit(qt_app.exec())
