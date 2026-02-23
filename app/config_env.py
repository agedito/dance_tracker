from pathlib import Path

from app.config import AppConfig


class ConfigEnvLoader:
    def __init__(self, env_path: str = "config.env"):
        self._env_path = Path(env_path)

    def load(self) -> AppConfig:
        values = self._read_values()
        radius = self._parse_positive_int(values.get("FRAME_CACHE_RADIUS"), AppConfig.frame_cache_radius)
        return AppConfig(frame_cache_radius=radius)

    def _read_values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        if not self._env_path.exists():
            return values

        for raw_line in self._env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()

        return values

    @staticmethod
    def _parse_positive_int(raw_value: str | None, default: int) -> int:
        if raw_value is None:
            return default
        try:
            parsed = int(raw_value)
            return parsed if parsed >= 0 else default
        except ValueError:
            return default
