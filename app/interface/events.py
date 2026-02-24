from dataclasses import dataclass
from typing import Callable


@dataclass
class AppEvents:
    on_frames_loaded: Callable[[str], None] = lambda _: None
