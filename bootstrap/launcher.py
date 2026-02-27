from app.interface.event_bus import EventBus
from app.track_app.adapter import AppAdapter
from app.track_app.config import Config as AppConfig
from app.track_app.main_app import DanceTrackerApp
from ui.config import Config as UiConfig
from ui.main_app import GraphicApp


def launch():
    # Dance tracker app
    app_cfg = AppConfig()
    app = DanceTrackerApp(app_cfg)

    # create event buses
    events = EventBus()
    adapter = AppAdapter(app, events)

    # Graphic user interface
    ui_cfg = UiConfig()
    ui_app = GraphicApp(adapter)
    ui_app.launch(ui_cfg, events)
