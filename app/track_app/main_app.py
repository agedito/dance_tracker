from app.track_app.services.music_identifier.ports import MusicIdentifierPort
from app.interface.track_detector import TrackDetectorPort
from app.track_app.config import Config
from app.track_app.frame_state.layers import default_layers
from app.track_app.frame_state.logic import ReviewState
from app.track_app.services.music_identifier.audio_extractor import AudioExtractor
from app.track_app.services.music_identifier.audd_client import AuddSongIdentifier
from app.track_app.services.music_identifier.service import MusicIdentifierService
from app.track_app.services.music_identifier.tempo_analyzer import ScipyTempoAnalyzer
from app.track_app.sections.track_detector.detection_api_adapter import DetectionApiPersonDetector
from app.track_app.sections.track_detector.mpvision_adapter import MPVisionPersonDetector
from app.track_app.sections.track_detector.mock_detectors import MockPersonDetector, NearbyMockPersonDetector
from app.track_app.sections.track_detector.service import TrackDetectorService
from services.detection.client import DetectionApiClient
from app.track_app.sections.video_manager.manager import VideoManager
from app.track_app.sections.video_manager.sequence_metadata_store import SequenceMetadataStore


class DanceTrackerApp:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.states_manager = ReviewState(total_frames=1200, fps=30, layers=default_layers(), config=cfg)
        self.video_manager = VideoManager()
        self.sequence_metadata = SequenceMetadataStore()
        self.music_identifier: MusicIdentifierPort = MusicIdentifierService(
            extractor=AudioExtractor(sample_seconds=cfg.audio_sample_seconds),
            identifier=AuddSongIdentifier(api_token=cfg.audd_api_token),
            analyzer=ScipyTempoAnalyzer(),
        )
        detection_api_detectors = _load_detection_api_detectors(cfg.detection_api_base_url, cfg.data_path)
        self.track_detector: TrackDetectorPort = TrackDetectorService(
            detectors={
                "Random detector": MockPersonDetector(),
                "Nearby random detector": NearbyMockPersonDetector(),
                "MPVision detector": MPVisionPersonDetector(),
                **detection_api_detectors,
            },
            default_detector_name="Random detector",
        )


def _load_detection_api_detectors(base_url: str, data_path: str = "", timeout: int = 5) -> dict:
    try:
        client = DetectionApiClient(base_url, timeout)
        caps = client.capabilities()
        return {
            provider: DetectionApiPersonDetector(client, provider, data_path=data_path)
            for provider in caps.get("providers", [])
        }
    except Exception:
        return {}
