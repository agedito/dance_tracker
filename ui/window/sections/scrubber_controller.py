from typing import Callable

from PySide6.QtCore import QTimer


class ScrubberController:
    """Throttles scrub: lightweight updates during drag, full update on release."""

    def __init__(
        self,
        set_proxy_enabled: Callable[[bool], None],
        on_frame: Callable[[int], None],
        on_frame_lightweight: Callable[[int], None],
    ):
        self._set_proxy_enabled = set_proxy_enabled
        self._on_frame = on_frame
        self._on_frame_lightweight = on_frame_lightweight
        self._scrubbing = False
        self._pending_scrub_frame: int | None = None
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._flush)

    def on_start(self) -> None:
        self._scrubbing = True
        self._pending_scrub_frame = None
        self._set_proxy_enabled(True)

    def on_end(self) -> None:
        self._scrubbing = False
        self._set_proxy_enabled(False)
        self._flush()

    def on_timeline_frame_changed(self, frame: int) -> None:
        if not self._scrubbing:
            self._on_frame(frame)
            return
        self._pending_scrub_frame = frame
        self._on_frame_lightweight(frame)
        if not self._timer.isActive():
            self._timer.start()

    def _flush(self) -> None:
        if self._pending_scrub_frame is None:
            return
        self._on_frame(self._pending_scrub_frame)
        self._pending_scrub_frame = None
