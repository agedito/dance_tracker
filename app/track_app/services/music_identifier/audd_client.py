import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.interface.music import SongMetadata, SongStatus


class AuddSongIdentifier:
    """Single responsibility: identify a song from an audio sample using audd.io."""

    def __init__(self, api_token: str = "", timeout_s: float = 12.0):
        self._api_token = api_token.strip()
        self._timeout_s = timeout_s

    def identify(self, audio_path: str) -> SongMetadata:
        if not self._api_token:
            return SongMetadata(
                status=SongStatus.UNAVAILABLE,
                provider="audd.io",
                message="Set AUDD_API_TOKEN to enable identification.",
            )

        sample_file = Path(audio_path)
        if not sample_file.exists() or not sample_file.is_file():
            return SongMetadata(
                status=SongStatus.ERROR,
                provider="audd.io",
                message="Could not read the audio sample.",
            )

        with sample_file.open("rb") as fd:
            audio_b64 = base64.b64encode(fd.read()).decode("ascii")

        payload = urllib.parse.urlencode(
            {
                "api_token": self._api_token,
                "return": "apple_music,spotify",
                "audio": audio_b64,
            }
        ).encode("utf-8")

        request = urllib.request.Request("https://api.audd.io/", data=payload, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=self._timeout_s) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as err:
            return SongMetadata(
                status=SongStatus.ERROR,
                provider="audd.io",
                message=f"Network error while identifying song: {err}",
            )

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return SongMetadata(
                status=SongStatus.ERROR,
                provider="audd.io",
                message="Invalid response from the identification service.",
            )

        result = data.get("result")
        if not result:
            return SongMetadata(
                status=SongStatus.NOT_FOUND,
                provider="audd.io",
                message="Could not identify the song with this sample.",
            )

        return SongMetadata(
            status=SongStatus.IDENTIFIED,
            title=result.get("title") or "",
            artist=result.get("artist") or "",
            album=result.get("album") or "",
            provider="audd.io",
        )
