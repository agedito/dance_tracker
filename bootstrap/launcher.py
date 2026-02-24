from bootstrap.config import AppConfig
from ui.launcher import launch as ui_launch


def launch(cfg: AppConfig | None = None):
    cfg = cfg or AppConfig()
    ui_launch(cfg)
