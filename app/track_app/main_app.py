from app.track_app.services.music_identifier.ports import MusicIdentifierPort
from app.interface.track_detector import TrackDetectorPort
from app.track_app.config import Config
from app.track_app.frame_state.layers import default_layers
from app.track_app.frame_state.logic import ReviewState
from app.track_app.services.music_identifier.audio_extractor import AudioExtractor
from app.track_app.services.music_identifier.audd_client import AuddSongIdentifier
from app.track_app.services.music_identifier.service import MusicIdentifierService
from app.track_app.services.music_identifier.tempo_analyzer import ScipyTempoAnalyzer
from app.track_app.sections.track_detector.mpvision_adapter import MPVisionPersonDetector
from app.track_app.sections.track_detector.service import MockPersonDetector, NearbyMockPersonDetector, TrackDetectorService
from app.track_app.sections.video_manager.manager import VideoManager


class DanceTrackerApp:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.states_manager = ReviewState(total_frames=1200, fps=30, layers=default_layers(), config=cfg)
        self.video_manager = VideoManager()
        self.music_identifier: MusicIdentifierPort = MusicIdentifierService(
            extractor=AudioExtractor(sample_seconds=cfg.audio_sample_seconds),
            identifier=AuddSongIdentifier(api_token=cfg.audd_api_token),
            analyzer=ScipyTempoAnalyzer(),
        )
        self.track_detector: TrackDetectorPort = TrackDetectorService(
            detectors={
                "Random detector": MockPersonDetector(),
                "Nearby random detector": NearbyMockPersonDetector(),
                "MPVision detector": MPVisionPersonDetector(),
            },
            default_detector_name="Random detector",
        )
