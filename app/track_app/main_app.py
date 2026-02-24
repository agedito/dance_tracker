from app.track_app.config import Config
from app.track_app.frame_state.layers import default_layers
from app.track_app.frame_state.logic import ReviewState
from app.track_app.sections.video_manager.manager import VideoManager


class DanceTrackerApp:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.states_manager = ReviewState(total_frames=1200, fps=30, layers=default_layers(), config=cfg)
        self.video_manager = VideoManager()
