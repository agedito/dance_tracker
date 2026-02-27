from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    frame_cache_radius: int = 25
    preload_anchor_points: int = 3
    audd_api_token: str = ""
    audio_sample_seconds: int = 20
    max_recent_folders: int = 5

    model_config = SettingsConfigDict(
        frozen=True,
        env_file=("preferences/app.env", "secrets.env"),
    )
