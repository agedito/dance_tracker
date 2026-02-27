import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.track_app.sections.music_identifier.models import SongMetadata, SongStatus


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
                message="Configura AUDD_API_TOKEN para habilitar la identificación.",
            )

        sample_file = Path(audio_path)
        if not sample_file.exists() or not sample_file.is_file():
            return SongMetadata(
                status=SongStatus.ERROR,
                provider="audd.io",
                message="No se pudo leer la muestra de audio.",
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
                message=f"Error de red al identificar canción: {err}",
            )

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return SongMetadata(
                status=SongStatus.ERROR,
                provider="audd.io",
                message="Respuesta inválida del servicio de identificación.",
            )

        result = data.get("result")
        if not result:
            return SongMetadata(
                status=SongStatus.NOT_FOUND,
                provider="audd.io",
                message="No se pudo identificar la canción con esta muestra.",
            )

        return SongMetadata(
            status=SongStatus.IDENTIFIED,
            title=result.get("title") or "",
            artist=result.get("artist") or "",
            album=result.get("album") or "",
            provider="audd.io",
        )
