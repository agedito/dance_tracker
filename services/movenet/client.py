from pathlib import Path

from services.detection.client import DetectResponse, DetectionApiClient


class MoveNetClient:
    """Client wrapper for the MoveNet detection provider."""

    def __init__(
        self,
        base_url: str = "http://localhost:9000",
        data_path: str = "",
        timeout: int = 30,
        video_timeout: int = 600,
    ):
        self._client = DetectionApiClient(base_url=base_url, timeout=timeout, video_timeout=video_timeout)
        self._data_path = Path(data_path) if data_path else None

    def _relative_path(self, path: str) -> str:
        if self._data_path is None:
            return path
        try:
            return Path(path).relative_to(self._data_path).as_posix()
        except ValueError:
            return path

    def detect_frame(
        self,
        image_path: str,
        score_threshold: float = 0.4,
        max_results: int = 20,
    ) -> DetectResponse:
        return self._client.detect(
            image_path=self._relative_path(image_path),
            provider="movenet",
            score_threshold=score_threshold,
            max_results=max_results,
        )

    def detect_batch(
        self,
        folder_path: str,
        score_threshold: float = 0.4,
        max_results: int = 20,
    ) -> list[DetectResponse]:
        return self._client.detect_batch(
            folder_path=self._relative_path(folder_path),
            provider="movenet",
            score_threshold=score_threshold,
            max_results=max_results,
        )

    def detect_video(
        self,
        video_path: str,
        score_threshold: float = 0.4,
        max_results: int = 20,
        batch_size: int = 32,
    ) -> list[DetectResponse]:
        return self._client.batch_video(
            video_path=self._relative_path(video_path),
            provider="movenet",
            score_threshold=score_threshold,
            max_results=max_results,
            batch_size=batch_size,
            save_crops=False,
        )
