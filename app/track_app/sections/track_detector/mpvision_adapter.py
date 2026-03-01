from app.interface.track_detector import BoundingBox, PersonDetection, RelativeBoundingBox
from services.mediapipe.client import MPVisionClient
from services.mediapipe.requests import BBoxRequest


class MPVisionPersonDetector:
    def __init__(
        self,
        client: MPVisionClient | None = None,
        score_threshold: float = 0.4,
        max_results: int = 20,
    ):
        self._client = client or MPVisionClient()
        self._score_threshold = score_threshold
        self._max_results = max_results

    def detect_people_in_frame(
        self,
        frame_path: str,
        previous_detections: list[PersonDetection] | None = None,
    ) -> list[PersonDetection]:
        _ = previous_detections
        try:
            response = self._client.bbox(
                BBoxRequest(
                    image_path=frame_path,
                    score_threshold=self._score_threshold,
                    max_results=self._max_results,
                ),
                render=False,
            )
        except Exception:
            return []

        if response.image_width <= 0 or response.image_height <= 0:
            return []

        width = response.image_width
        height = response.image_height
        detections: list[PersonDetection] = []
        for person in response.persons:
            box = BoundingBox(
                x=person.x,
                y=person.y,
                width=person.width,
                height=person.height,
            )
            detections.append(
                PersonDetection(
                    confidence=float(person.score),
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
