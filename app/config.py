from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    frame_cache_radius: int = 25
