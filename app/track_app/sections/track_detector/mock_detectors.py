import random
from pathlib import Path

from app.interface.track_detector import BoundingBox, PersonDetection, RelativeBoundingBox


class MockPersonDetector:
    def detect_people_in_frame(
        self,
        frame_path: str,
        previous_detections: list[PersonDetection] | None = None,
    ) -> list[PersonDetection]:
        _ = previous_detections
        width, height = _image_size(frame_path)
        rng = random.Random(frame_path)

        left_box = _random_box(
            rng=rng,
            width=width,
            height=height,
            min_x_ratio=0.05,
            max_x_ratio=0.35,
        )
        right_box = _random_box(
            rng=rng,
            width=width,
            height=height,
            min_x_ratio=0.55,
            max_x_ratio=0.85,
        )

        return [
            _to_detection(rng, left_box, width, height),
            _to_detection(rng, right_box, width, height),
        ]


class NearbyMockPersonDetector:
    def detect_people_in_frame(
        self,
        frame_path: str,
        previous_detections: list[PersonDetection] | None = None,
    ) -> list[PersonDetection]:
        width, height = _image_size(frame_path)
        rng = random.Random(frame_path)

        if not previous_detections:
            return MockPersonDetector().detect_people_in_frame(frame_path=frame_path)

        detections: list[PersonDetection] = []
        for prev in previous_detections:
            box = _jitter_box_from_previous(rng=rng, previous=prev.bbox_relative, width=width, height=height)
            detections.append(_to_detection(rng=rng, box=box, width=width, height=height))
        return detections


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _random_box(rng: random.Random, width: int, height: int, min_x_ratio: float, max_x_ratio: float) -> BoundingBox:
    box_width = max(20, int(width * rng.uniform(0.16, 0.28)))
    box_height = max(20, int(height * rng.uniform(0.30, 0.55)))
    max_x = max(0, int(width * max_x_ratio) - box_width)
    min_x = max(0, min(max_x, int(width * min_x_ratio)))
    x = rng.randint(min_x, max_x if max_x >= min_x else min_x)

    max_y = max(0, height - box_height)
    min_y = max(0, int(height * 0.05))
    y = rng.randint(min_y, max_y if max_y >= min_y else min_y)
    return BoundingBox(x=x, y=y, width=box_width, height=box_height)


def _jitter_box_from_previous(rng: random.Random, previous: RelativeBoundingBox, width: int, height: int) -> BoundingBox:
    prev_x = previous.x * width
    prev_y = previous.y * height
    prev_width = previous.width * width
    prev_height = previous.height * height

    new_width = max(20, int(prev_width * rng.uniform(0.92, 1.08)))
    new_height = max(20, int(prev_height * rng.uniform(0.92, 1.08)))

    x_shift = int(width * rng.uniform(-0.03, 0.03))
    y_shift = int(height * rng.uniform(-0.03, 0.03))

    x = int(prev_x) + x_shift
    y = int(prev_y) + y_shift

    x = max(0, min(x, max(0, width - new_width)))
    y = max(0, min(y, max(0, height - new_height)))
    return BoundingBox(x=x, y=y, width=new_width, height=new_height)


def _to_detection(rng: random.Random, box: BoundingBox, width: int, height: int) -> PersonDetection:
    return PersonDetection(
        confidence=round(rng.uniform(0.7, 0.99), 3),
        bbox_pixels=box,
        bbox_relative=RelativeBoundingBox(
            x=box.x / width,
            y=box.y / height,
            width=box.width / width,
            height=box.height / height,
        ),
    )


# ── Image size helpers ────────────────────────────────────────────────────────

def _image_size(frame_path: str) -> tuple[int, int]:
    path = Path(frame_path)
    if not path.exists():
        return 1920, 1080

    try:
        with path.open("rb") as fh:
            header = fh.read(32)
            if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
                width = int.from_bytes(header[16:20], "big")
                height = int.from_bytes(header[20:24], "big")
                if width > 0 and height > 0:
                    return width, height

            if header.startswith(b"BM") and len(header) >= 26:
                fh.seek(18)
                dib = fh.read(8)
                width = int.from_bytes(dib[0:4], "little")
                height = int.from_bytes(dib[4:8], "little")
                if width > 0 and height > 0:
                    return width, abs(height)

            fh.seek(0)
            data = fh.read()
            jpeg_size = _jpeg_size(data)
            if jpeg_size is not None:
                return jpeg_size
    except OSError:
        return 1920, 1080

    return 1920, 1080


def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        return None

    idx = 2
    while idx + 9 < len(data):
        if data[idx] != 0xFF:
            idx += 1
            continue

        marker = data[idx + 1]
        idx += 2

        if marker in {0xD8, 0xD9}:
            continue

        if idx + 2 > len(data):
            return None

        segment_length = int.from_bytes(data[idx:idx + 2], "big")
        if segment_length < 2 or idx + segment_length > len(data):
            return None

        if marker in {0xC0, 0xC2}:
            if idx + 7 >= len(data):
                return None
            height = int.from_bytes(data[idx + 3:idx + 5], "big")
            width = int.from_bytes(data[idx + 5:idx + 7], "big")
            if width > 0 and height > 0:
                return width, height
            return None

        idx += segment_length

    return None
