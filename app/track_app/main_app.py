from app.track_app.services.music_identifier.ports import MusicIdentifierPort
from app.interface.track_detector import TrackDetectorPort
from app.track_app.config import Config
from app.track_app.frame_state.layers import default_layers
from app.track_app.frame_state.logic import ReviewState
from app.track_app.services.music_identifier.audio_extractor import AudioExtractor
from app.track_app.services.music_identifier.audd_client import AuddSongIdentifier
from app.track_app.services.music_identifier.service import MusicIdentifierService
from app.track_app.services.music_identifier.tempo_analyzer import ScipyTempoAnalyzer
from app.interface.pose_detector import PoseDetectorPort
from app.interface.segmentation import SegmentationPort
from app.track_app.sections.track_detector.detection_api_adapter import DetectionApiPersonDetector
from app.track_app.sections.track_detector.pose_api_adapter import PoseApiDetector
from app.track_app.sections.track_detector.pose_service import PoseDetectorService
from app.track_app.sections.track_detector.segmentation_api_adapter import SegmentationApiAdapter
from app.track_app.sections.track_detector.segmentation_service import SegmentationService
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
        detectors, capabilities, pose_detectors, seg_detectors = _load_from_capabilities(
            cfg.detection_api_base_url, cfg.data_path
        )
        self.track_detector: TrackDetectorPort = TrackDetectorService(
            detectors=detectors,
            default_detector_name=next(iter(detectors), ""),
            capabilities=capabilities,
        )
        self.pose_detector: PoseDetectorPort = PoseDetectorService(
            detectors=pose_detectors,
            default_provider=next(iter(pose_detectors), ""),
        )
        self.segmentation: SegmentationPort = SegmentationService(
            detectors=seg_detectors,
            default_provider=next(iter(seg_detectors), ""),
        )


def _load_from_capabilities(base_url: str, data_path: str = "", timeout: int = 5):
    try:
        client = DetectionApiClient(base_url, timeout=timeout)
        capabilities = client.capabilities()

        detection_cap = capabilities.get("detection")
        detection_providers = detection_cap.providers if detection_cap else []
        detect_client = DetectionApiClient(base_url, timeout=30, video_timeout=600)
        detectors = {
            provider: DetectionApiPersonDetector(detect_client, provider, data_path=data_path)
            for provider in detection_providers
        }

        pose_cap = capabilities.get("pose")
        pose_providers = pose_cap.providers if pose_cap else []
        pose_client = DetectionApiClient(base_url, timeout=30, video_timeout=600)
        pose_detectors = {
            provider: PoseApiDetector(pose_client, provider, data_path=data_path)
            for provider in pose_providers
        }

        seg_cap = capabilities.get("segmentation")
        seg_providers = seg_cap.providers if seg_cap else []
        seg_client = DetectionApiClient(base_url, timeout=60, video_timeout=600)
        seg_detectors = {
            provider: SegmentationApiAdapter(seg_client, provider, data_path=data_path)
            for provider in seg_providers
        }

        return detectors, capabilities, pose_detectors, seg_detectors
    except Exception:
        return {}, {}, {}, {}
