import json
from pathlib import Path

from app.interface.segmentation import SegmentInfo, SegmentationResult


class SegmentationStore:
    """Single responsibility: read and write segmentations.json for a frames folder."""

    @staticmethod
    def json_path(frames_folder_path: str) -> Path:
        return Path(frames_folder_path).expanduser().parent / "segmentations.json"

    @staticmethod
    def write(
        frames_folder_path: str,
        provider: str,
        segmentations: dict[int, SegmentationResult],
    ) -> None:
        frames_folder = Path(frames_folder_path).expanduser()

        def _relative(abs_path: str | None) -> str | None:
            if not abs_path:
                return abs_path
            try:
                return Path(abs_path).relative_to(frames_folder).as_posix()
            except ValueError:
                return abs_path

        payload = {
            "provider": provider,
            "frames": {
                str(idx): {
                    "mask_path": _relative(result.mask_path),
                    "segments": [
                        {
                            "category_id": s.category_id,
                            "name": s.name,
                            "pixel_count": s.pixel_count,
                            "percentage": s.percentage,
                        }
                        for s in result.segments
                    ],
                }
                for idx, result in segmentations.items()
            },
        }
        SegmentationStore.json_path(frames_folder_path).write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    @staticmethod
    def read(
        frames_folder_path: str,
    ) -> tuple[dict[int, SegmentationResult], str | None]:
        path = SegmentationStore.json_path(frames_folder_path)
        if not path.exists():
            return {}, None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}, None

        if not isinstance(payload, dict):
            return {}, None

        provider = payload.get("provider")
        saved_provider = provider if isinstance(provider, str) else None

        frames_data = payload.get("frames")
        if not isinstance(frames_data, dict):
            return {}, saved_provider

        frames_folder = Path(frames_folder_path).expanduser()

        def _absolute(rel_path: str | None) -> str | None:
            if not rel_path:
                return rel_path
            candidate = frames_folder / rel_path
            return str(candidate)

        result: dict[int, SegmentationResult] = {}
        for key, item in frames_data.items():
            if not isinstance(key, str) or not key.isdigit() or not isinstance(item, dict):
                continue
            seg = _parse_segmentation(item, _absolute)
            if seg is not None:
                result[int(key)] = seg

        return result, saved_provider


def _parse_segmentation(
    data: dict,
    resolve_path,
) -> SegmentationResult | None:
    raw_mask = data.get("mask_path")
    mask_path = resolve_path(raw_mask) if isinstance(raw_mask, str) else None

    raw_segments = data.get("segments", [])
    segments: list[SegmentInfo] = []
    if isinstance(raw_segments, list):
        for s in raw_segments:
            if not isinstance(s, dict):
                continue
            try:
                segments.append(SegmentInfo(
                    category_id=int(s.get("category_id", 0)),
                    name=str(s.get("name", "")),
                    pixel_count=int(s.get("pixel_count", 0)),
                    percentage=float(s.get("percentage", 0.0)),
                ))
            except (TypeError, ValueError):
                continue

    return SegmentationResult(mask_path=mask_path, segments=tuple(segments))
