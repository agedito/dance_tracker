from app.interface.event_bus import EventBus
from app.track_app.adapter import AppAdapter
from app.track_app.config import Config as AppConfig
from app.track_app.main_app import DanceTrackerApp
from ui.config import Config as UiConfig
from ui.main_app import GraphicApp


def launch():
    app_cfg = AppConfig()
    app = DanceTrackerApp(app_cfg)

    events = EventBus()
    adapter = AppAdapter(app, events)

    ui_cfg = UiConfig()
    ui_app = GraphicApp(adapter)
    ui_app.launch(ui_cfg, events)
