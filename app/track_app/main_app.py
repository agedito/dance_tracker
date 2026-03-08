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
        detectors, capabilities = _load_from_capabilities(cfg.detection_api_base_url, cfg.data_path)
        self.track_detector: TrackDetectorPort = TrackDetectorService(
            detectors=detectors,
            default_detector_name=next(iter(detectors), ""),
            capabilities=capabilities,
        )


def _load_from_capabilities(base_url: str, data_path: str = "", timeout: int = 5):
    try:
        client = DetectionApiClient(base_url, timeout=timeout)
        capabilities = client.capabilities()
        detection_providers = capabilities.get("detection", None)
        providers = detection_providers.providers if detection_providers else []
        detect_client = DetectionApiClient(base_url, timeout=30, video_timeout=600)
        detectors = {
            provider: DetectionApiPersonDetector(detect_client, provider, data_path=data_path)
            for provider in providers
        }
        return detectors, capabilities
    except Exception:
        return {}, {}
