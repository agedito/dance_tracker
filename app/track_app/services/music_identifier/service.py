from app.interface.music import SongMetadata, SongStatus
from app.track_app.services.music_identifier.ports import (
    AudioSampleExtractorPort,
    AudioSongRecognizerPort,
    AudioTempoAnalyzerPort,
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

        identified_song = self._identifier.identify(audio_sample)
        analysis = self._analyzer.analyze(audio_sample)
        return SongMetadata(
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

    def analyze_tempo_from_video(self, video_path: str) -> SongMetadata:
        audio_sample = self._extractor.extract_sample(video_path)
        if not audio_sample:
            return SongMetadata(
                status=SongStatus.UNAVAILABLE,
                provider="ffmpeg",
                message="Could not extract audio for tempo analysis.",
            )

        analysis = self._analyzer.analyze(audio_sample)
        return SongMetadata(
            status=analysis.status,
            message=analysis.message,
            tempo_bpm=analysis.tempo_bpm,
            pulse_count=analysis.pulse_count,
            audio_duration_s=analysis.audio_duration_s,
            analysis_provider=analysis.analysis_provider,
        )

    @staticmethod
    def _merge_message(song_message: str, analysis_message: str) -> str:
        if song_message and analysis_message:
            return f"{song_message} Tempo analysis: {analysis_message}"
        return song_message or analysis_message
