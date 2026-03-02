from collections.abc import Callable
from typing import Protocol


class MediaPort(Protocol):
    def load(
        self,
        path: str,
        on_progress: Callable[[int], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> None: ...
