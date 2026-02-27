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


class SongStatus:
    NOT_RUN = "not_run"
    IDENTIFIED = "identified"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class AudioSampleExtractorPort(Protocol):
    def extract_sample(self, video_path: str) -> str | None: ...


class AudioSongRecognizerPort(Protocol):
    def identify(self, audio_path: str) -> SongMetadata: ...


class MusicIdentifierPort(Protocol):
    def identify_from_video(self, video_path: str) -> SongMetadata: ...
