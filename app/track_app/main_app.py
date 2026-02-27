import logging

from app.interface.music import MusicIdentifierPort
from app.interface.track_detector import TrackDetectorPort
from app.track_app.config import Config
from app.track_app.frame_state.layers import default_layers
from app.track_app.frame_state.logic import ReviewState
from app.track_app.services.music_identifier.audio_extractor import AudioExtractor
from app.track_app.services.music_identifier.audd_client import AuddSongIdentifier
from app.track_app.services.music_identifier.service import MusicIdentifierService
from app.track_app.sections.track_detector.service import (
    MockPersonDetector,
    TrackDetectorService,
    YoloNasPersonDetector,
)
from app.track_app.sections.video_manager.manager import VideoManager


logger = logging.getLogger(__name__)


class DanceTrackerApp:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.states_manager = ReviewState(total_frames=1200, fps=30, layers=default_layers(), config=cfg)
        self.video_manager = VideoManager()
        self.music_identifier: MusicIdentifierPort = MusicIdentifierService(
            extractor=AudioExtractor(sample_seconds=cfg.audio_sample_seconds),
            identifier=AuddSongIdentifier(api_token=cfg.audd_api_token),
        )
        detector = self._build_person_detector()
        self.track_detector: TrackDetectorPort = TrackDetectorService(detector=detector)

    def _build_person_detector(self):
        if self.cfg.detector_backend != "yolo_nas":
            logger.info(
                "YOLO-NAS disabled by configuration. Selected detector backend: %s",
                self.cfg.detector_backend,
            )
            return MockPersonDetector()

        available, reason = YoloNasPersonDetector.availability_status()
        if available:
            logger.info("YOLO-NAS is available: %s", reason)
            return YoloNasPersonDetector(
                model_name=self.cfg.yolo_nas_model_name,
                confidence_threshold=self.cfg.yolo_nas_confidence_threshold,
            )

        logger.warning("YOLO-NAS is not available. Cause: %s", reason)
        return MockPersonDetector()
