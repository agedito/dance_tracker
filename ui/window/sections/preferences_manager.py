import re
from pathlib import Path

from ui.window.preferences import load_preferences, save_preferences


class PreferencesManager:
    """Single responsibility: persist and retrieve user preferences."""

    def __init__(self, max_recent_folders: int):
        self._prefs = load_preferences()
        self._max_recent = max_recent_folders

    # ── Generic access ───────────────────────────────────────────────

    def get(self, key: str, default=None):
        return self._prefs.get(key, default)

    def set(self, key: str, value):
        self._prefs[key] = value

    def save(self):
        save_preferences(self._prefs)

    # ── Recent folders ───────────────────────────────────────────────

    def recent_folders(self) -> list[str]:
        saved = self._prefs.get("recent_folders", [])
        if not isinstance(saved, list):
            return []
        folders = [item for item in saved if isinstance(item, str) and item]
        return folders[: self._max_recent]

    def register_recent_folder(self, folder_path: str):
        normalized = str(Path(folder_path).expanduser())
        folders = [p for p in self.recent_folders() if p != normalized]
        folders.insert(0, normalized)
        self._prefs["recent_folders"] = folders[: self._max_recent]
        self._prefs["last_opened_folder"] = normalized
        self._remember_folder_thumbnail(normalized)
        self.save()

    def remove_recent_folder(self, folder_path: str):
        folders = [p for p in self.recent_folders() if p != folder_path]
        self._prefs["recent_folders"] = folders[: self._max_recent]
        thumbnails = self._prefs.get("recent_folder_thumbnails", {})
        if isinstance(thumbnails, dict):
            thumbnails.pop(folder_path, None)
            self._prefs["recent_folder_thumbnails"] = thumbnails
        self.save()

    def thumbnail_for_folder(self, folder_path: str) -> str | None:
        thumbnails = self._prefs.get("recent_folder_thumbnails", {})
        if not isinstance(thumbnails, dict):
            return None

        thumbnail = thumbnails.get(folder_path)
        if not isinstance(thumbnail, str) or not thumbnail:
            return None

        return thumbnail if Path(thumbnail).is_file() else None

    def last_opened_folder(self) -> str | None:
        val = self._prefs.get("last_opened_folder")
        return val if isinstance(val, str) and val else None

    # ── Frame memory per folder ──────────────────────────────────────

    def saved_frame_for_folder(self, folder_path: str) -> int:
        frames = self._prefs.get("last_frame_by_folder", {})
        if not isinstance(frames, dict):
            return 0
        frame = frames.get(folder_path, 0)
        return frame if isinstance(frame, int) else 0

    def remember_frame(self, folder_path: str | None, cur_frame: int):
        if not folder_path:
            return
        frames = self._prefs.get("last_frame_by_folder", {})
        if not isinstance(frames, dict):
            frames = {}
        frames[folder_path] = cur_frame
        self._prefs["last_frame_by_folder"] = frames
        self._prefs["last_opened_folder"] = folder_path
        self.save()

    # ── Splitter layout ──────────────────────────────────────────────

    def splitter_sizes(self, name: str) -> list[int] | None:
        val = self._prefs.get(f"{name}_sizes")
        if isinstance(val, list) and len(val) == 2:
            return val
        return None

    def save_splitter_sizes(self, name: str, sizes: list[int]):
        self._prefs[f"{name}_sizes"] = sizes

    def save_fullscreen(self, is_fullscreen: bool):
        self._prefs["fullscreen"] = is_fullscreen

    # ── Recent folder thumbnails ────────────────────────────────────

    def _remember_folder_thumbnail(self, folder_path: str):
        thumbnail = self._thumbnail_from_frame(folder_path)
        thumbnails = self._prefs.get("recent_folder_thumbnails", {})
        if not isinstance(thumbnails, dict):
            thumbnails = {}

        if thumbnail is None:
            thumbnails.pop(folder_path, None)
        else:
            thumbnails[folder_path] = thumbnail

        self._prefs["recent_folder_thumbnails"] = thumbnails

    def _thumbnail_from_frame(self, folder_path: str) -> str | None:
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return None

        valid_suffixes = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
        frame_files = [
            file
            for file in sorted(folder.iterdir(), key=self._natural_sort_key)
            if file.is_file() and file.suffix.lower() in valid_suffixes
        ]
        if not frame_files:
            return None

        target_idx = 300 if len(frame_files) > 300 else len(frame_files) // 2
        return str(frame_files[target_idx])

    @staticmethod
    def _natural_sort_key(path: Path):
        chunks = re.split(r"(\d+)", path.name.lower())
        return [int(chunk) if chunk.isdigit() else chunk for chunk in chunks]
