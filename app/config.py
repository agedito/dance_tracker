from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    frame_cache_radius: int = 25

    @classmethod
    def from_env_file(cls, env_path: str = "config.env") -> "AppConfig":
        values: dict[str, str] = {}
        path = Path(env_path)
        if path.exists():
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()

        radius = cls._parse_positive_int(values.get("FRAME_CACHE_RADIUS"), cls.frame_cache_radius)
        return cls(frame_cache_radius=radius)

    @staticmethod
    def _parse_positive_int(raw_value: str | None, default: int) -> int:
        if raw_value is None:
            return default
        try:
            parsed = int(raw_value)
            return parsed if parsed >= 0 else default
        except ValueError:
            return default
