import shutil
import subprocess
from pathlib import Path


class AudioExtractor:
    """Single responsibility: extract a lightweight audio sample from a video file."""

    def __init__(self, sample_seconds: int = 20):
        self._sample_seconds = max(1, sample_seconds)

    def extract_sample(self, video_path: str) -> str | None:
        ffmpeg = self._resolve_ffmpeg_executable()
        if ffmpeg is None:
            return None

        source = Path(video_path)
        if not source.exists() or not source.is_file():
            return None

        target = source.parent / f"{source.stem}_music_sample.wav"
        if target.exists():
            target.unlink()

        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "44100",
            "-t",
            str(self._sample_seconds),
            str(target),
        ]

        completed = subprocess.run(cmd, capture_output=True, text=True)
        if completed.returncode != 0 or not target.exists() or target.stat().st_size == 0:
            if target.exists():
                target.unlink()
            return None

        return str(target)

    @staticmethod
    def _resolve_ffmpeg_executable() -> str | None:
        """Prefer system ffmpeg, fallback to the imageio-ffmpeg bundled binary."""
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg is not None:
            return system_ffmpeg

        try:
            import imageio_ffmpeg

            bundled_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return None

        return bundled_ffmpeg if bundled_ffmpeg else None
