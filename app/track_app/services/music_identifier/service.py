from pathlib import Path

from app.interface.music import (
    AudioSampleExtractorPort,
    AudioSongRecognizerPort,
    AudioTempoAnalyzerPort,
    SongMetadata,
    SongStatus,
)


class MusicIdentifierService:
    """Orchestrate extraction, song identification, and local tempo analysis."""

    def __init__(
        self,
        extractor: AudioSampleExtractorPort,
        identifier: AudioSongRecognizerPort,
        analyzer: AudioTempoAnalyzerPort,
    ):
        self._extractor = extractor
        self._identifier = identifier
        self._analyzer = analyzer

    def identify_from_video(self, video_path: str) -> SongMetadata:
        audio_sample = self._extractor.extract_sample(video_path)
        if not audio_sample:
            return SongMetadata(
                status=SongStatus.UNAVAILABLE,
                provider="ffmpeg",
                message="Could not extract audio (install ffmpeg to enable it).",
            )

        try:
            identified_song = self._identifier.identify(audio_sample)
            analysis = self._analyzer.analyze(audio_sample)
        finally:
            self._delete_temporary_sample(audio_sample)

        merged = SongMetadata(
            status=identified_song.status,
            title=identified_song.title,
            artist=identified_song.artist,
            album=identified_song.album,
            provider=identified_song.provider,
            message=self._merge_message(identified_song.message, analysis.message),
            tempo_bpm=analysis.tempo_bpm,
            pulse_count=analysis.pulse_count,
            audio_duration_s=analysis.audio_duration_s,
            analysis_provider=analysis.analysis_provider,
        )

        return merged

    @staticmethod
    def _merge_message(song_message: str, analysis_message: str) -> str:
        if song_message and analysis_message:
            return f"{song_message} Tempo analysis: {analysis_message}"
        return song_message or analysis_message

    @staticmethod
    def _delete_temporary_sample(audio_sample: str) -> None:
        audio_file = Path(audio_sample)
        if audio_file.exists():
            audio_file.unlink(missing_ok=True)
