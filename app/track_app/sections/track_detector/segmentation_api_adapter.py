import logging
from pathlib import Path

from app.interface.segmentation import SegmentInfo, SegmentationResult
from services.detection.client import DetectionApiClient, SegmentFrameResult

log = logging.getLogger(__name__)


class SegmentationApiAdapter:
    def __init__(self, client: DetectionApiClient, provider: str, data_path: str = ""):
        self._client = client
        self._provider = provider
        self._data_path = Path(data_path) if data_path else None

    def _relative_path(self, path: str) -> str:
        if self._data_path is None:
            return path
        try:
            return Path(path).relative_to(self._data_path).as_posix()
        except ValueError:
            return path

    def _absolute_path(self, rel_path: str | None) -> str | None:
        if not rel_path or self._data_path is None:
            return rel_path
        candidate = self._data_path / rel_path
        return str(candidate) if candidate.exists() else rel_path

    def _output_name_for(self, frame_path: str) -> str:
        stem = Path(frame_path).stem
        return f"{stem}_segmentation.png"

    def _map_frame(self, result: SegmentFrameResult) -> SegmentationResult:
        segments = tuple(
            SegmentInfo(
                category_id=int(s.get("category_id", 0)),
                name=str(s.get("name", "")),
                pixel_count=int(s.get("pixel_count", 0)),
                percentage=float(s.get("percentage", 0.0)),
            )
            for s in result.segments
            if isinstance(s, dict)
        )
        return SegmentationResult(
            mask_path=self._absolute_path(result.output_path),
            segments=segments,
        )

    def detect_in_frame(self, frame_path: str) -> SegmentationResult | None:
        output_name = self._output_name_for(frame_path)
        try:
            result = self._client.segment(
                self._relative_path(frame_path), self._provider, output_name
            )
        except Exception as e:
            log.error("[%s] segment frame failed: %s", self._provider, e)
            return None
        return self._map_frame(result)

    def detect_in_batch(self, folder_path: str) -> list[SegmentationResult | None]:
        try:
            results = self._client.segment_batch(
                self._relative_path(folder_path), self._provider
            )
        except Exception as e:
            log.error("[%s] segment batch failed: %s", self._provider, e)
            return []
        return [self._map_frame(r) for r in results]

