import logging

from app.interface.track_detector import BoundingBox, PersonDetection, RelativeBoundingBox
from services.movenet.client import MoveNetClient

log = logging.getLogger(__name__)


class MoveNetPersonDetector:
    def __init__(
        self,
        client: MoveNetClient | None = None,
        base_url: str = "http://localhost:9000",
        data_path: str = "",
        score_threshold: float = 0.4,
        max_results: int = 20,
    ):
        self._client = client or MoveNetClient(base_url=base_url, data_path=data_path)
        self._score_threshold = score_threshold
        self._max_results = max_results

    def _map_response(
        self,
        image_width: int,
        image_height: int,
        persons,
        fallback_size: tuple[int, int] = (0, 0),
    ) -> list[PersonDetection]:
        width = image_width if image_width > 0 else fallback_size[0]
        height = image_height if image_height > 0 else fallback_size[1]
        if width <= 0 or height <= 0:
            return []

        detections: list[PersonDetection] = []
        for person in persons:
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
            response = self._client.detect_frame(
                image_path=frame_path,
                score_threshold=self._score_threshold,
                max_results=self._max_results,
            )
        except Exception as err:
            log.error("[movenet] detect frame failed: %s", err)
            return []

        return self._map_response(
            image_width=response.image_width,
            image_height=response.image_height,
            persons=response.persons,
        )

    def detect_people_in_batch(
        self,
        folder_path: str,
        image_size: tuple[int, int] = (0, 0),
    ) -> list[list[PersonDetection]]:
        try:
            responses = self._client.detect_batch(
                folder_path=folder_path,
                score_threshold=self._score_threshold,
                max_results=self._max_results,
            )
        except Exception as err:
            log.error("[movenet] detect batch failed: %s", err)
            return []

        return [
            self._map_response(
                image_width=response.image_width,
                image_height=response.image_height,
                persons=response.persons,
                fallback_size=image_size,
            )
            for response in responses
        ]

    def detect_people_in_video(
        self,
        video_path: str,
        image_size: tuple[int, int] = (0, 0),
    ) -> list[list[PersonDetection]]:
        try:
            responses = self._client.detect_video(
                video_path=video_path,
                score_threshold=self._score_threshold,
                max_results=self._max_results,
            )
        except Exception as err:
            log.error("[movenet] detect video failed: %s", err)
            return []

        return [
            self._map_response(
                image_width=response.image_width,
                image_height=response.image_height,
                persons=response.persons,
                fallback_size=image_size,
            )
            for response in responses
        ]
