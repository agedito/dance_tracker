from app.config import Config
from app.frame_state.layers import default_layers
from app.frame_state.logic import ReviewState


class DanceTrackerApp:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.states_manager = ReviewState(total_frames=1200, fps=30, layers=default_layers(), config=cfg)
