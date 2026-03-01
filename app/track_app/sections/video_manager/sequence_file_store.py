"""Single responsibility: read and write .dance_tracker.json files for sequence data."""
import json
from pathlib import Path

_SUFFIX = ".dance_tracker.json"


def find_metadata_for_frames(frames_folder: Path) -> Path | None:
    """Return the metadata file whose 'frames' entry resolves to frames_folder, or None."""
    target = frames_folder.resolve()
    for metadata_path in sorted(frames_folder.parent.glob(f"*{_SUFFIX}")):
        payload = read(metadata_path)
        if not payload:
            continue
        frames_value = payload.get("frames") or payload.get("frames_path")
        resolved = resolve_path(frames_value, metadata_path.parent)
        if resolved and resolved == target:
            return metadata_path
    return None


def read(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def write_payload(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_path(value: object, root: Path) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()
    return candidate


def video_path_from_metadata(metadata: dict) -> str | None:
    """Extract the video file name/path from a .dance_tracker.json payload."""
    legacy = metadata.get("video_path")
    if isinstance(legacy, str) and legacy.strip():
        return legacy

    video_data = metadata.get("video")
    if not isinstance(video_data, dict):
        return None

    name = video_data.get("name") or video_data.get("nombre")
    if not isinstance(name, str) or not name.strip():
        return None

    return name
