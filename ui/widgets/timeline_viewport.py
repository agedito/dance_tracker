from utils.numbers import clamp


class TimelineViewport:
    """Manages view_start/view_span state and converts between screen and timeline coordinates."""

    def __init__(self):
        self.view_start = 0.0
        self.view_span = 1.0
        self.panning = False
        self.pan_anchor_x = 0.0
        self.pan_anchor_start = 0.0

    @property
    def visible_end(self) -> float:
        return self.view_start + self.view_span

    def set(self, start: float, span: float) -> bool:
        """Update viewport. Returns True if the visible region actually changed."""
        old_start, old_span = self.view_start, self.view_span
        self.view_start = start
        self.view_span = span
        self._normalize()
        return (
            abs(self.view_start - old_start) > 1e-9
            or abs(self.view_span - old_span) > 1e-9
        )

    def _normalize(self):
        self.view_span = clamp(self.view_span, 0.01, 1.0)
        self.view_start = clamp(self.view_start, 0.0, 1.0 - self.view_span)

    def zoom_at(self, x: float, width: int, zoom_in: bool) -> bool:
        """Zoom in/out centred at pixel x. Returns True if viewport changed."""
        old_start, old_span = self.view_start, self.view_span
        anchor = clamp(x / max(1, width), 0.0, 1.0)
        anchor_frame = self.view_start + anchor * self.view_span
        factor = 0.84 if zoom_in else 1.19
        self.view_span = self.view_span * factor
        self._normalize()
        self.view_start = anchor_frame - anchor * self.view_span
        self._normalize()
        return abs(self.view_start - old_start) > 1e-9 or abs(self.view_span - old_span) > 1e-9

    def start_pan(self, x: float) -> None:
        self.panning = True
        self.pan_anchor_x = x
        self.pan_anchor_start = self.view_start

    def stop_pan(self) -> None:
        self.panning = False

    def pan_to(self, current_x: float, width: int) -> bool:
        """Pan to cursor position relative to the pan anchor. Returns True if changed."""
        if width <= 1:
            return False
        delta = ((current_x - self.pan_anchor_x) / width) * self.view_span
        return self.set(self.pan_anchor_start - delta, self.view_span)

    def frame_x(self, frame: int, total_frames: int, width: int) -> int:
        """Screen x coordinate for a frame. Returns -1000 if outside the visible range."""
        norm_frame = clamp(frame, 0, total_frames - 1) / max(1, total_frames - 1)
        if norm_frame < self.view_start or norm_frame > self.visible_end:
            return -1000
        relative = (norm_frame - self.view_start) / max(0.0001, self.view_span)
        return int(relative * width)

    def frame_from_pos(self, x: float, width: int, total_frames: int) -> int:
        """Timeline frame index for screen pixel x."""
        norm_x = clamp(x, 0.0, float(width))
        view_pos = self.view_start + (norm_x / max(1, width)) * self.view_span
        return int(round(clamp(view_pos, 0.0, 1.0) * (total_frames - 1)))
