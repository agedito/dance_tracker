import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class DetectBBox:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class DetectPerson:
    id: int
    bbox: DetectBBox
    score: float
    center_x: int
    center_y: int
    crop_path: str | None


@dataclass(frozen=True)
class DetectResponse:
    provider: str
    num_persons: int
    image_width: int
    image_height: int
    persons: list[DetectPerson]
    output_path: str | None
    elapsed_ms: float


class DetectionApiClient:
    def __init__(self, base_url: str = "http://localhost:9000", timeout: int = 5):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def capabilities(self) -> dict:
        req = urllib.request.Request(self._base_url + "/capabilities/detection")
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read())

    def detect(
            self,
            image_path: str,
            provider: str,
            score_threshold: float = 0.4,
            max_results: int = 2,
    ) -> DetectResponse:
        url = (
            f"{self._base_url}/api/detect"
            f"?provider={urllib.parse.quote(provider)}&render=false"
        )
        body = json.dumps({
            "image_path": image_path,
            "score_threshold": score_threshold,
            "max_results": max_results,
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            raw = json.loads(resp.read())
        return _parse_detect_response(raw)

    def detect_batch(
            self,
            folder_path: str,
            provider: str,
            score_threshold: float = 0.4,
            max_results: int = 20,
    ) -> list[DetectResponse]:
        url = (
            f"{self._base_url}/api/detect/batch"
            f"?provider={urllib.parse.quote(provider)}&render=false"
        )
        body = json.dumps({
            "folder_path": folder_path,
            "score_threshold": score_threshold,
            "max_results": max_results,
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            raw = json.loads(resp.read())
        return [_parse_detect_response(r) for r in raw]

    def batch_video(
            self,
            video_path: str,
            provider: str,
            score_threshold: float = 0.4,
            max_results: int = 50,
            batch_size: int = 32,
            save_crops: bool = False,
    ) -> list[DetectResponse]:
        url = (
            f"{self._base_url}/api/detect/video"
            f"?provider={urllib.parse.quote(provider)}&render=false"
        )
        body = json.dumps({
            "video_path": video_path,
            "score_threshold": score_threshold,
            "max_results": max_results,
            "batch_size": batch_size,
            "save_crops": save_crops,
        }).encode("utf-8")
        print(url)
        print(body)
        t0 = time.time()
        print("Requesting....")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        tn = time.time()
        print("...request done")
        print(f"Elapsed: {tn - t0:.2f}s")
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            raw = json.loads(resp.read())
        print(raw)
        return [_parse_detect_response(r) for r in raw]


def _parse_detect_response(raw: dict) -> DetectResponse:
    persons = [
        DetectPerson(
            id=p["id"],
            bbox=DetectBBox(
                x=p["bbox"]["x"],
                y=p["bbox"]["y"],
                width=p["bbox"]["width"],
                height=p["bbox"]["height"],
            ),
            score=float(p["score"]),
            center_x=p["center_x"],
            center_y=p["center_y"],
            crop_path=p.get("crop_path"),
        )
        for p in raw.get("persons", [])
    ]
    return DetectResponse(
        provider=raw["provider"],
        num_persons=raw["num_persons"],
        image_width=raw["image_width"],
        image_height=raw["image_height"],
        persons=persons,
        output_path=raw.get("output_path"),
        elapsed_ms=float(raw.get("elapsed_ms", 0.0)),
    )
