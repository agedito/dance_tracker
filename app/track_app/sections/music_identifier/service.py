from app.interface.music import (
    AudioSampleExtractorPort,
    AudioSongRecognizerPort,
    SongMetadata,
    SongStatus,
)


class MusicIdentifierService:
    """Single responsibility: orchestrate extraction + identification for a video."""

    def __init__(self, extractor: AudioSampleExtractorPort, identifier: AudioSongRecognizerPort):
        self._extractor = extractor
        self._identifier = identifier

    def identify_from_video(self, video_path: str) -> SongMetadata:
        audio_sample = self._extractor.extract_sample(video_path)
        if not audio_sample:
            return SongMetadata(
                status=SongStatus.UNAVAILABLE,
                provider="ffmpeg",
                message="No se pudo extraer audio (verifica la instalación de dependencias).",
            )

        return self._identifier.identify(audio_sample)
