from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SongMetadata:
    status: str
    title: str = ""
    artist: str = ""
    album: str = ""
    provider: str = ""
    message: str = ""
    tempo_bpm: float | None = None
    pulse_count: int | None = None
    audio_duration_s: float | None = None
    analysis_provider: str = ""


class SongStatus:
    NOT_RUN = "not_run"
    IDENTIFIED = "identified"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class MusicPort(Protocol):
    def analyze_for_sequence(self, frames_folder_path: str) -> SongMetadata: ...
