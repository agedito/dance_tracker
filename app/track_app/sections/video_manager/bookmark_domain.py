"""Pure bookmark business rules — no I/O, no filesystem access."""
from app.interface.sequence_data import Bookmark

MIN_BOOKMARK_DISTANCE_FRAMES = 25


def normalize_name(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def extract_bookmarks(payload: dict) -> list[Bookmark]:
    sequence = payload.get("sequence")
    if not isinstance(sequence, dict):
        return []

    raw_bookmarks = sequence.get("bookmarks")
    if not isinstance(raw_bookmarks, list):
        return []

    values: dict[int, Bookmark] = {}
    for raw in raw_bookmarks:
        if isinstance(raw, dict):
            frame = _to_int(raw.get("frame"))
            name = normalize_name(raw.get("name"))
            locked = bool(raw.get("locked", False))
        else:
            frame = _to_int(raw)
            name = ""
            locked = False

        if frame < 0:
            continue
        values[frame] = Bookmark(frame=frame, name=name, locked=locked)

    return [values[f] for f in sorted(values)]


def insert_bookmark(
    bookmarks: list[Bookmark],
    frame: int,
    name: str = "",
    locked: bool = False,
    allow_nearby: bool = False,
) -> list[Bookmark]:
    normalized = max(0, int(frame))
    normalized_name = normalize_name(name)
    by_frame = {b.frame: b for b in bookmarks}

    if not allow_nearby and _is_too_close(bookmarks, normalized):
        return [by_frame[f] for f in sorted(by_frame)]

    by_frame[normalized] = Bookmark(frame=normalized, name=normalized_name, locked=locked)
    return [by_frame[f] for f in sorted(by_frame)]


def apply_move(bookmarks: list[Bookmark], source_frame: int, target_frame: int) -> list[Bookmark]:
    source = next((b for b in bookmarks if b.frame == source_frame), None)
    if source is None or source.locked:
        return bookmarks

    without_source = [b for b in bookmarks if b.frame != source_frame]
    preferred_direction = 1 if source_frame > target_frame else -1
    adjusted = _resolve_move_target(without_source, target_frame, preferred_direction)
    return insert_bookmark(without_source, adjusted, source.name, locked=source.locked, allow_nearby=False)


def _resolve_move_target(bookmarks: list[Bookmark], target_frame: int, preferred_direction: int) -> int:
    candidate = max(0, int(target_frame))
    if not _is_too_close(bookmarks, candidate):
        return candidate

    direction = 1 if preferred_direction >= 0 else -1
    while True:
        conflict = _find_conflict(bookmarks, candidate)
        if conflict is None:
            return candidate

        if direction > 0:
            candidate = conflict + MIN_BOOKMARK_DISTANCE_FRAMES
            continue

        next_candidate = conflict - MIN_BOOKMARK_DISTANCE_FRAMES
        if next_candidate < 0:
            direction = 1
            continue
        candidate = next_candidate


def _find_conflict(bookmarks: list[Bookmark], frame: int) -> int | None:
    for b in sorted(bookmarks, key=lambda item: abs(item.frame - frame)):
        if abs(b.frame - frame) < MIN_BOOKMARK_DISTANCE_FRAMES:
            return b.frame
    return None


def _is_too_close(bookmarks: list[Bookmark], frame: int) -> bool:
    return _find_conflict(bookmarks, frame) is not None


def _to_int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
