from dataclasses import dataclass


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
