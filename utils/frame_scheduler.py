"""Shared frame-processing order logic.

Used by both the frame preloader (UI cache) and the detection streaming service
so that any background frame-processing task covers the timeline in the same
spread-out pattern: current frame → start → end → mid → quartiles → bookmarks,
then filling gaps by assigning each remaining frame to its nearest anchor.
"""


class FrameScheduler:
    @staticmethod
    def make_anchors(
        total_frames: int,
        bookmarks: list[int] = (),
        current_frame: int = 0,
    ) -> list[int]:
        """Return deduplicated anchor indices in priority order."""
        if total_frames <= 0:
            return []
        candidates = [
            current_frame,
            0,
            total_frames - 1,
            total_frames // 2,
            total_frames // 4,
            3 * total_frames // 4,
            *bookmarks,
        ]
        seen: set[int] = set()
        result: list[int] = []
        for a in candidates:
            if 0 <= a < total_frames and a not in seen:
                seen.add(a)
                result.append(a)
        return result

    @staticmethod
    def build_order(total_frames: int, anchors: list[int]) -> list[int]:
        """Return all frame indices in processing order.

        Each frame is assigned to its nearest anchor, then sorted within that
        group by distance. Groups are interleaved round-robin so that all
        regions of the timeline are covered early rather than processing
        sequentially from start to end.
        """
        if total_frames <= 0:
            return []
        if not anchors:
            return list(range(total_frames))

        groups: dict[int, list[int]] = {a: [] for a in anchors}
        for f in range(total_frames):
            nearest = min(anchors, key=lambda a, f=f: abs(a - f))
            groups[nearest].append(f)

        for anchor in anchors:
            groups[anchor].sort(key=lambda f: abs(f - anchor))

        order: list[int] = []
        iters = [iter(groups[a]) for a in anchors]
        active = list(iters)
        while active:
            next_active = []
            for it in active:
                try:
                    order.append(next(it))
                    next_active.append(it)
                except StopIteration:
                    pass
            active = next_active
        return order
