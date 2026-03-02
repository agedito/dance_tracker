import json
import logging
from pathlib import Path

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
        except Exception as e:
            log.error("[%s] detect frame failed: %s", self._provider, e)
            return []
        return self._map_response(response)

    def detect_people_in_video(self, video_path: str) -> list[list[PersonDetection]]:
        try:
            summary = self._client.batch_video(
                video_path=self._relative_path(video_path),
                provider=self._provider,
                score_threshold=self._score_threshold,
                max_results=self._max_results,
            )
        except Exception as e:
            log.error("[%s] detect_video failed: %s", self._provider, e)
            return []

        if not summary.json_path:
            log.warning("[%s] detect_video: no json_path in response", self._provider)
            return []
        if self._data_path is None:
            log.warning("[%s] detect_video: DATA_PATH not set, cannot read results", self._provider)
            return []

        results_file = self._data_path / summary.json_path
        try:
            raw = json.loads(results_file.read_text(encoding="utf-8"))
        except Exception as e:
            log.error("[%s] detect_video: cannot read %s: %s", self._provider, results_file, e)
            return []

        return self._parse_video_json(raw, summary.total_frames)

    def _parse_video_json(self, raw: object, total_frames: int) -> list[list[PersonDetection]]:
        """Parse the server-side detections JSON saved by batch_video."""
        log.debug("[%s] video json keys: %s", self._provider, list(raw.keys()) if isinstance(raw, dict) else type(raw))
        if not isinstance(raw, dict):
            return []

        # Expect {"frames": [{"frame_index": N, "image_width": W, "image_height": H, "persons": [...]}, ...]}
        frames_data = raw.get("frames") or raw.get("results") or []
        if not isinstance(frames_data, list):
            return []

        result: list[list[PersonDetection]] = [[] for _ in range(total_frames)]
        for frame in frames_data:
            if not isinstance(frame, dict):
                continue
            idx = frame.get("frame_index")
            if not isinstance(idx, int) or idx < 0 or idx >= total_frames:
                continue
            from services.detection.client import DetectBBox, DetectPerson, DetectResponse
            try:
                response = DetectResponse(
                    provider=self._provider,
                    num_persons=frame.get("num_persons", 0),
                    image_width=frame["image_width"],
                    image_height=frame["image_height"],
                    persons=[
                        DetectPerson(
                            id=p["id"],
                            bbox=DetectBBox(
                                x=p["bbox"]["x"], y=p["bbox"]["y"],
                                width=p["bbox"]["width"], height=p["bbox"]["height"],
                            ),
                            score=float(p["score"]),
                            center_x=p["center_x"],
                            center_y=p["center_y"],
                            crop_path=p.get("crop_path"),
                        )
                        for p in frame.get("persons", [])
                    ],
                    output_path=None,
                    elapsed_ms=0.0,
                )
            except (KeyError, TypeError):
                continue
            result[idx] = self._map_response(response)
        return result

    def detect_people_in_batch(self, folder_path: str) -> list[list[PersonDetection]]:
        try:
            responses = self._client.detect_batch(
                folder_path=self._relative_path(folder_path),
                provider=self._provider,
                score_threshold=self._score_threshold,
                max_results=self._max_results,
            )
        except Exception as e:
            log.error("[%s] detect_batch failed: %s", self._provider, e)
            return []
        return [self._map_response(r) for r in responses]
