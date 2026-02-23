import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    frame_cache_radius: int = 25


def load_config(config_path: Path | None = None) -> AppConfig:
    path = config_path or Path(__file__).resolve().parent.parent / "config.json"
    if not path.exists():
        return AppConfig()

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return AppConfig(frame_cache_radius=max(0, int(data.get("frame_cache_radius", 25))))
