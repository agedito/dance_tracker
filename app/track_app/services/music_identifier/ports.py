from typing import Protocol

from app.interface.music import SongMetadata


class AudioSampleExtractorPort(Protocol):
    def extract_sample(self, video_path: str) -> str | None: ...


class AudioSongRecognizerPort(Protocol):
    def identify(self, audio_path: str) -> SongMetadata: ...


class AudioTempoAnalyzerPort(Protocol):
    def analyze(self, audio_path: str) -> SongMetadata: ...


class MusicIdentifierPort(Protocol):
    def identify_from_video(self, video_path: str) -> SongMetadata: ...

    def analyze_tempo_from_video(self, video_path: str) -> SongMetadata: ...
