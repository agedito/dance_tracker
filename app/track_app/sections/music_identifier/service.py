from app.track_app.sections.music_identifier.audio_extractor import AudioExtractor
from app.track_app.sections.music_identifier.audd_client import AuddSongIdentifier
from app.track_app.sections.music_identifier.models import SongMetadata, SongStatus


class MusicIdentifierService:
    """Single responsibility: orchestrate extraction + identification for a video."""

    def __init__(self, extractor: AudioExtractor, identifier: AuddSongIdentifier):
        self._extractor = extractor
        self._identifier = identifier

    def identify_from_video(self, video_path: str) -> SongMetadata:
        audio_sample = self._extractor.extract_sample(video_path)
        if not audio_sample:
            return SongMetadata(
                status=SongStatus.UNAVAILABLE,
                provider="ffmpeg",
                message="No se pudo extraer audio (instala ffmpeg para habilitarlo).",
            )

        return self._identifier.identify(audio_sample)
