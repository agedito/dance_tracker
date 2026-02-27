from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
APP_ENV_PATH = ROOT_DIR / "preferences" / "app.env"
SECRETS_ENV_PATH = ROOT_DIR / "secrets.env"


class Config(BaseSettings):
    frame_cache_radius: int = 25
    preload_anchor_points: int = Field(default=3, validation_alias="PRELOAD_ANCHOR_POINTS")
    audd_api_token: str = ""
    audio_sample_seconds: int = 20
    max_recent_folders: int = 5

    model_config = SettingsConfigDict(
        frozen=True,
        env_file=(APP_ENV_PATH, SECRETS_ENV_PATH),
    )
