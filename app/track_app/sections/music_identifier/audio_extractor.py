import re
import shutil
import subprocess
from pathlib import Path


class AudioExtractor:
    """Single responsibility: extract a lightweight audio sample from a video file."""

    def __init__(self, sample_seconds: int = 20, sample_points: int = 3):
        self._sample_seconds = max(1, sample_seconds)
        self._sample_points = max(2, sample_points)

    def extract_sample(self, video_path: str) -> str | None:
        ffmpeg = self._resolve_ffmpeg_executable()
        if ffmpeg is None:
            return None

        source = Path(video_path)
        if not source.exists() or not source.is_file():
            return None

        duration_seconds = self._read_duration_seconds(source=source, ffmpeg=ffmpeg)
        if duration_seconds is None:
            return None

        target = source.parent / f"{source.stem}_music_sample.wav"
        if target.exists():
            target.unlink()

        starts = self._build_sample_starts(duration_seconds=duration_seconds)
        cmd = self._build_ffmpeg_concat_command(ffmpeg=ffmpeg, source=source, target=target, starts=starts)

        completed = subprocess.run(cmd, capture_output=True, text=True)
        if completed.returncode != 0 or not target.exists() or target.stat().st_size == 0:
            if target.exists():
                target.unlink()
            return None

        return str(target)

    def _build_sample_starts(self, duration_seconds: float) -> list[float]:
        max_start = max(0.0, duration_seconds - float(self._sample_seconds))
        if self._sample_points == 2:
            return [0.0, max_start]
        return [max_start * index / (self._sample_points - 1) for index in range(self._sample_points)]

    def _build_ffmpeg_concat_command(self, ffmpeg: str, source: Path, target: Path, starts: list[float]) -> list[str]:
        parts: list[str] = []
        labels: list[str] = []

        for index, start in enumerate(starts):
            end = start + float(self._sample_seconds)
            sample_label = f"a{index}"
            labels.append(f"[{sample_label}]")
            parts.append(
                f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[{sample_label}]"
            )

        parts.append(f"{''.join(labels)}concat=n={len(starts)}:v=0:a=1[outa]")

        return [
            ffmpeg,
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "44100",
            "-filter_complex",
            ";".join(parts),
            "-map",
            "[outa]",
            str(target),
        ]

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

    @staticmethod
    def _read_duration_seconds(source: Path, ffmpeg: str) -> float | None:
        completed = subprocess.run(
            [ffmpeg, "-i", str(source)],
            capture_output=True,
            text=True,
        )
        output = f"{completed.stdout}\n{completed.stderr}"
        matched = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", output)
        if not matched:
            return None

        hours = int(matched.group(1))
        minutes = int(matched.group(2))
        seconds = float(matched.group(3))
        return (hours * 3600) + (minutes * 60) + seconds
