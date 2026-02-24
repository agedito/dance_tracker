from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

env_file = "preferences/ui.env"
css_file = "preferences/ui.qss"


class Config(BaseSettings):
    fullscreen: bool = True
    title: str = "Dance Tracker app"
    max_recent_folders: int = 5

    model_config = SettingsConfigDict(frozen=True, env_file=env_file)

    @staticmethod
    def get_css() -> str:
        return Path(css_file).read_text()
