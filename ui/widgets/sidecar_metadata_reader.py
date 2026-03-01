import json
import re
from pathlib import Path

_VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def _natural_sort_key(path: Path):
    chunks = re.split(r"(\d+)", path.name.lower())
    return [int(chunk) if chunk.isdigit() else chunk for chunk in chunks]


class SidecarMetadataReader:
    def find_proxy_files(self, folder: Path, frame_files: list[Path]) -> list[Path]:
        expected_count = len(frame_files)
        proxy_dir = self._proxy_dir_from_metadata(folder)
        if proxy_dir is None:
            proxy_dir = folder.parent / "low_frames"
        if proxy_dir is None or not proxy_dir.exists() or not proxy_dir.is_dir():
            proxy_dir = folder.parent / "frames_mino"
        if not proxy_dir.exists() or not proxy_dir.is_dir():
            return []

        proxy_files = [
            p
            for p in sorted(proxy_dir.iterdir(), key=_natural_sort_key)
            if p.is_file() and p.suffix.lower() in _VALID_SUFFIXES
        ]
        return proxy_files if len(proxy_files) == expected_count else []

    def read_bookmark_anchor_frames(self, folder: Path, total_frames: int) -> list[int]:
        if total_frames <= 0:
            return []

        for metadata_file in folder.parent.glob("*.json"):
            payload = _read_json_dict(metadata_file)
            if payload is None:
                continue

            frames_value = payload.get("frames") or payload.get("frames_path")
            if not isinstance(frames_value, str):
                continue

            resolved_frames = _resolve_metadata_path(frames_value, metadata_file.parent)
            if resolved_frames != folder.resolve():
                continue

            return _extract_bookmark_frames(payload, total_frames)

        return []

    def _proxy_dir_from_metadata(self, folder: Path) -> Path | None:
        for metadata_file in folder.parent.glob("*.json"):
            try:
                payload = json.loads(metadata_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue

            if not isinstance(payload, dict):
                continue

            frames_value = payload.get("frames") or payload.get("frames_path")
            low_frames_value = payload.get("low_frames")
            if not isinstance(frames_value, str) or not isinstance(low_frames_value, str):
                continue

            resolved_frames = _resolve_metadata_path(frames_value, metadata_file.parent)
            if resolved_frames != folder.resolve():
                continue

            return _resolve_metadata_path(low_frames_value, metadata_file.parent)

        return None


def _resolve_metadata_path(value: str, root: Path) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    return (root / candidate).resolve()


def _read_json_dict(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _extract_bookmark_frames(payload: dict, total_frames: int) -> list[int]:
    sequence = payload.get("sequence")
    if not isinstance(sequence, dict):
        return []

    raw_bookmarks = sequence.get("bookmarks")
    if not isinstance(raw_bookmarks, list):
        return []

    frames: list[int] = []
    for raw_bookmark in raw_bookmarks:
        if isinstance(raw_bookmark, dict):
            frame_value = raw_bookmark.get("frame")
        else:
            frame_value = raw_bookmark

        try:
            frame = int(frame_value)
        except (TypeError, ValueError):
            continue

        if 0 <= frame < total_frames and frame not in frames:
            frames.append(frame)

    return sorted(frames)
