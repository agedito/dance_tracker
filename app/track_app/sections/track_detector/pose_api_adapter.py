import logging
from pathlib import Path

from app.interface.pose_detector import PoseDetection, PoseLandmark
from services.detection.client import DetectionApiClient, PoseFrameResult

log = logging.getLogger(__name__)


class PoseApiDetector:
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

    def _map_frame(self, result: PoseFrameResult) -> list[PoseDetection]:
        poses: list[PoseDetection] = []
        for raw_landmarks in result.poses:
            landmarks: list[PoseLandmark] = []
            for lm in raw_landmarks:
                if not isinstance(lm, dict):
                    continue
                try:
                    landmarks.append(PoseLandmark(
                        index=int(lm["index"]),
                        name=str(lm.get("name", "")),
                        x=float(lm["x"]),
                        y=float(lm["y"]),
                        z=float(lm.get("z", 0.0)),
                        visibility=float(lm.get("visibility", 1.0)),
                    ))
                except (KeyError, TypeError, ValueError):
                    continue
            if landmarks:
                poses.append(PoseDetection(landmarks=tuple(landmarks)))
        return poses

    def detect_in_frame(self, frame_path: str) -> list[PoseDetection]:
        try:
            result = self._client.pose(self._relative_path(frame_path), self._provider)
        except Exception as e:
            log.error("[%s] pose frame failed: %s", self._provider, e)
            return []
        return self._map_frame(result)

    def detect_in_batch(self, folder_path: str) -> list[list[PoseDetection]]:
        try:
            results = self._client.pose_batch(self._relative_path(folder_path), self._provider)
        except Exception as e:
            log.error("[%s] pose batch failed: %s", self._provider, e)
            return []
        return [self._map_frame(r) for r in results]

    def detect_in_video(self, video_path: str) -> list[list[PoseDetection]]:
        try:
            results = self._client.pose_video(self._relative_path(video_path), self._provider)
        except Exception as e:
            log.error("[%s] pose video failed: %s", self._provider, e)
            return []
        return [self._map_frame(r) for r in results]
