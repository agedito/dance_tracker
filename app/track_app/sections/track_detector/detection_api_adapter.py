from pathlib import Path

from app.interface.track_detector import BoundingBox, PersonDetection, RelativeBoundingBox
from services.detection.client import DetectResponse, DetectionApiClient


class DetectionApiPersonDetector:
    def __init__(
        self,
        client: DetectionApiClient,
        provider: str,
        data_path: str = "",
        score_threshold: float = 0.4,
        max_results: int = 20,
    ):
        self._client = client
        self._provider = provider
        self._data_path = Path(data_path) if data_path else None
        self._score_threshold = score_threshold
        self._max_results = max_results

    def _relative_path(self, frame_path: str) -> str:
        if self._data_path is None:
            return frame_path
        try:
            return Path(frame_path).relative_to(self._data_path).as_posix()
        except ValueError:
            return frame_path

    def _map_response(self, response: DetectResponse) -> list[PersonDetection]:
        if response.image_width <= 0 or response.image_height <= 0:
            return []
        width = response.image_width
        height = response.image_height
        detections: list[PersonDetection] = []
        for person in response.persons:
            box = BoundingBox(
                x=person.bbox.x,
                y=person.bbox.y,
                width=person.bbox.width,
                height=person.bbox.height,
            )
            detections.append(
                PersonDetection(
                    confidence=person.score,
                    bbox_pixels=box,
                    bbox_relative=RelativeBoundingBox(
                        x=box.x / width,
                        y=box.y / height,
                        width=box.width / width,
                        height=box.height / height,
                    ),
                )
            )
        return detections

    def detect_people_in_frame(
        self,
        frame_path: str,
        previous_detections: list[PersonDetection] | None = None,
    ) -> list[PersonDetection]:
        _ = previous_detections
        try:
            response = self._client.detect(
                image_path=self._relative_path(frame_path),
                provider=self._provider,
                score_threshold=self._score_threshold,
                max_results=self._max_results,
            )
        except Exception:
            return []
        return self._map_response(response)

    def detect_people_in_batch(self, folder_path: str) -> list[list[PersonDetection]]:
        try:
            responses = self._client.detect_batch(
                folder_path=self._relative_path(folder_path),
                provider=self._provider,
                score_threshold=self._score_threshold,
                max_results=self._max_results,
            )
        except Exception:
            return []
        return [self._map_response(r) for r in responses]
