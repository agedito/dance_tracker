from app.config import Config as AppConfig
from app.main_app import DanceTrackerApp
from ui.config import Config as UiConfig
from ui.main_app import GraphicApp


def launch():
    # Dance tracker app
    app_cfg = AppConfig()
    app = DanceTrackerApp(app_cfg)

    # Graphic user interface
    ui = GraphicApp(app)
    ui_cfg = UiConfig()
    ui.launch(ui_cfg)
