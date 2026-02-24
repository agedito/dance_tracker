from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    fullscreen: bool = True
    title: str = "Dance Tracker app"

    model_config = SettingsConfigDict(frozen=True, env_file="ui.env")
