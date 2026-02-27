from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    frame_cache_radius: int = 25
    audd_api_token: str = ""
    audio_sample_seconds: int = 20
    max_recent_folders: int = 5
    detector_backend: str = "yolo_nas"
    yolo_nas_model_name: str = "yolo_nas_s"
    yolo_nas_confidence_threshold: float = 0.35

    model_config = SettingsConfigDict(
        frozen=True,
        env_file=("preferences/app.env", "secrets.env"),
    )
