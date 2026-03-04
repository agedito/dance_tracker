import logging
from pathlib import Path

import cv2

from app.interface.track_detector import BoundingBox, PersonDetection, RelativeBoundingBox
from services.detection.client import DetectResponse, DetectionApiClient

log = logging.getLogger(__name__)


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

    def _map_response(
            self,
            response: DetectResponse,
            fallback_size: tuple[int, int] = (0, 0),
            target_size: tuple[int, int] | None = None,
    ) -> list[PersonDetection]:
        width = response.image_width if response.image_width > 0 else fallback_size[0]
        height = response.image_height if response.image_height > 0 else fallback_size[1]
        if width <= 0 or height <= 0:
            return []

        target_width = width
        target_height = height
        if target_size:
            requested_width, requested_height = target_size
            if requested_width > 0 and requested_height > 0:
                target_width = requested_width
                target_height = requested_height

        scale_x = target_width / width if width > 0 else 1.0
        scale_y = target_height / height if height > 0 else 1.0

        detections: list[PersonDetection] = []
        for person in response.persons:
            box = BoundingBox(
                x=round(person.bbox.x * scale_x),
                y=round(person.bbox.y * scale_y),
                width=round(person.bbox.width * scale_x),
                height=round(person.bbox.height * scale_y),
            )
            detections.append(
                PersonDetection(
                    confidence=person.score,
                    bbox_pixels=box,
                    bbox_relative=RelativeBoundingBox(
                        x=box.x / target_width,
                        y=box.y / target_height,
                        width=box.width / target_width,
                        height=box.height / target_height,
                    ),
                )
            )
        return detections

    def _resolve_low_res_frame(self, frame_path: str) -> tuple[str, tuple[int, int] | None]:
        source = Path(frame_path)
        if source.parent.name != "frames":
            return frame_path, None

        for sibling_name in ("low_frames", "frames_mino"):
            candidate = source.parent.parent / sibling_name / source.name
            if candidate.is_file():
                return str(candidate), self._read_image_size(source)
        return frame_path, None

    @staticmethod
    def _resolve_low_res_folder(folder_path: str) -> str:
        source = Path(folder_path)
        if source.name != "frames":
            return folder_path
        for sibling_name in ("low_frames", "frames_mino"):
            candidate = source.parent / sibling_name
            if candidate.is_dir():
                return str(candidate)
        return folder_path

    @staticmethod
    def _read_image_size(image_path: Path) -> tuple[int, int] | None:
        image = cv2.imread(str(image_path))
        if image is None:
            return None
        height, width = image.shape[:2]
        if width <= 0 or height <= 0:
            return None
        return width, height

    def detect_people_in_frame(
            self,
            frame_path: str,
            previous_detections: list[PersonDetection] | None = None,
    ) -> list[PersonDetection]:
        _ = previous_detections
        detection_frame_path, target_size = self._resolve_low_res_frame(frame_path)
        try:
            response = self._client.detect(
                image_path=self._relative_path(detection_frame_path),
                provider=self._provider,
                score_threshold=self._score_threshold,
                max_results=self._max_results,
            )
        except Exception as e:
            log.error("[%s] detect frame failed: %s", self._provider, e)
            return []
        return self._map_response(response, target_size=target_size)

    def detect_people_in_video(
            self,
            video_path: str,
            image_size: tuple[int, int] = (0, 0),
    ) -> list[list[PersonDetection]]:
        try:
            responses = self._client.batch_video(
                video_path=self._relative_path(video_path),
                provider=self._provider,
                score_threshold=self._score_threshold,
                max_results=self._max_results,
            )
        except Exception as e:
            log.error("[%s] detect_video failed: %s", self._provider, e)
            return []
        return [self._map_response(r, fallback_size=image_size, target_size=image_size) for r in responses]

    def detect_people_in_batch(
            self,
            folder_path: str,
            image_size: tuple[int, int] = (0, 0),
    ) -> list[list[PersonDetection]]:
        try:
            responses = self._client.detect_batch(
                folder_path=self._relative_path(self._resolve_low_res_folder(folder_path)),
                provider=self._provider,
                score_threshold=self._score_threshold,
                max_results=self._max_results,
            )
        except Exception as e:
            log.error("[%s] detect_batch failed: %s", self._provider, e)
            return []
        return [self._map_response(r, fallback_size=image_size, target_size=image_size) for r in responses]
