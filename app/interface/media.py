from typing import Protocol


class MediaPort(Protocol):
    def load(self, path: str) -> None: ...
