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

    def _output_name_for(self, frame_path: str) -> str:
        stem = Path(frame_path).stem
        return f"segmentation/{stem}_segmentation.png"

    def _map_frame(self, result: SegmentFrameResult, frames_folder: Path) -> SegmentationResult:
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
        mask_path: str | None = None
        if result.output_path:
            candidate = frames_folder / result.output_path
            mask_path = str(candidate)
        return SegmentationResult(mask_path=mask_path, segments=segments)

    def detect_in_frame(self, frame_path: str) -> SegmentationResult | None:
        frames_folder = Path(frame_path).parent
        output_name = self._output_name_for(frame_path)
        try:
            result = self._client.segment(
                self._relative_path(frame_path), self._provider, output_name
            )
        except Exception as e:
            log.error("[%s] segment frame failed: %s", self._provider, e)
            return None
        return self._map_frame(result, frames_folder)

    def detect_in_batch(self, folder_path: str) -> list[SegmentationResult | None]:
        frames_folder = Path(folder_path)
        try:
            results = self._client.segment_batch(
                self._relative_path(folder_path), self._provider
            )
        except Exception as e:
            log.error("[%s] segment batch failed: %s", self._provider, e)
            return []
        return [self._map_frame(r, frames_folder) for r in results]
