from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    frame_cache_radius: int = 25

    model_config = SettingsConfigDict(frozen=True, env_file="preferences/app.env")
