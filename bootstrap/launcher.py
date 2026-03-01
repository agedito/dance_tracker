from app.interface.event_bus import EventBus
from app.track_app.adapter import AppAdapter
from app.track_app.config import Config as AppConfig
from app.track_app.main_app import DanceTrackerApp
from ui.config import Config as UiConfig
from ui.main_app import GraphicApp
from ui.window.sections.preferences_manager import PreferencesManager


def launch():
    # App domain
    app_cfg = AppConfig()
    app = DanceTrackerApp(app_cfg)

    # Preferences are the single owner of ~/.dance_tracker_prefs.json.
    # Created here so the same instance is shared with both the app adapter
    # (via SequencePreferencesPort) and the UI (MainWindow).
    prefs = PreferencesManager(app_cfg.max_recent_folders)

    events = EventBus()
    adapter = AppAdapter(app, events, prefs)

    # Graphic user interface
    ui_cfg = UiConfig()
    ui_app = GraphicApp(adapter)
    ui_app.launch(ui_cfg, events, prefs)
