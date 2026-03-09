import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from app.interface.track_detector import CapabilityInfo, EndpointInfo
from utils.timer import Timer


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
class VideoDetectSummary:
    provider: str
    source: str
    total_frames: int
    processed: int
    failed: int
    json_path: str | None
    elapsed_ms: float


@dataclass(frozen=True)
class PoseFrameResult:
    frame_index: int
    image_width: int
    image_height: int
    poses: list[list[dict]]  # list of poses, each pose is a list of landmark dicts


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
    def __init__(self, base_url: str = "http://localhost:9000", timeout: int = 5, video_timeout: int = 600):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._video_timeout = video_timeout

    def capabilities(self) -> dict[str, CapabilityInfo]:
        url = self._base_url + "/capabilities"
        print(f"[DetectionApiClient] GET {url}")
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            raw = json.loads(resp.read())
        return _parse_capabilities(raw)

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
        print(f"[DetectionApiClient] POST {url}  body={body.decode()}")

        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with Timer(f"detect {provider} {image_path}"):
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = json.loads(resp.read())
                print(raw)

        provider = raw["provider"]
        frames = raw.get("frames", [])
        if not frames:
            return DetectResponse(provider=provider, num_persons=0, image_width=0,
                                  image_height=0, persons=[], output_path=None,
                                  elapsed_ms=float(raw.get("elapsed_ms", 0.0)))
        return _parse_detect_response({"provider": provider, "frame": frames[0],
                                       "elapsed_ms": raw.get("elapsed_ms", 0.0)})

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
        print(f"[DetectionApiClient] POST {url}  body={body.decode()}")

        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with Timer(f"detect_batch {provider} {folder_path}"):
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = json.loads(resp.read())
                print(raw)

        provider = raw["provider"]
        frames = sorted(raw.get("frames", []), key=lambda f: f.get("frame_index", 0))
        return [_parse_detect_response({"provider": provider, "frame": f}) for f in frames]

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
        print(f"[DetectionApiClient] POST {url}  body={body.decode()}")

        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with Timer(f"batch_video {provider} {video_path}"):
            with urllib.request.urlopen(req, timeout=self._video_timeout) as resp:
                raw = json.loads(resp.read())
                print(raw)

        provider = raw["provider"]
        frames = sorted(raw.get("frames", []), key=lambda f: f.get("frame_index", 0))
        return [_parse_detect_response({"provider": provider, "frame": f}) for f in frames]


    def pose(self, image_path: str, provider: str) -> PoseFrameResult:
        url = f"{self._base_url}/api/pose?provider={urllib.parse.quote(provider)}"
        body = json.dumps({"image_path": image_path}).encode("utf-8")
        print(f"[DetectionApiClient] POST {url}  body={body.decode()}")

        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            raw = json.loads(resp.read())
            print(raw)

        frames = raw.get("frames", [])
        if not frames:
            return PoseFrameResult(frame_index=0, image_width=0, image_height=0, poses=[])
        return _parse_pose_frame(frames[0])

    def pose_batch(self, folder_path: str, provider: str) -> list[PoseFrameResult]:
        url = f"{self._base_url}/api/pose/batch?provider={urllib.parse.quote(provider)}"
        body = json.dumps({"folder_path": folder_path}).encode("utf-8")
        print(f"[DetectionApiClient] POST {url}  body={body.decode()}")

        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            raw = json.loads(resp.read())
            print(raw)

        frames = sorted(raw.get("frames", []), key=lambda f: f.get("frame_index", 0))
        return [_parse_pose_frame(f) for f in frames]

    def pose_video(self, video_path: str, provider: str) -> list[PoseFrameResult]:
        url = f"{self._base_url}/api/pose/video?provider={urllib.parse.quote(provider)}"
        body = json.dumps({"video_path": video_path}).encode("utf-8")
        print(f"[DetectionApiClient] POST {url}  body={body.decode()}")

        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=self._video_timeout) as resp:
            raw = json.loads(resp.read())
            print(raw)

        frames = sorted(raw.get("frames", []), key=lambda f: f.get("frame_index", 0))
        return [_parse_pose_frame(f) for f in frames]


def _parse_pose_frame(raw: dict) -> PoseFrameResult:
    poses_raw = raw.get("poses", [])
    poses = [p.get("landmarks", []) for p in poses_raw if isinstance(p, dict)]
    return PoseFrameResult(
        frame_index=int(raw.get("frame_index", 0)),
        image_width=int(raw.get("image_width", 0)),
        image_height=int(raw.get("image_height", 0)),
        poses=poses,
    )


def _parse_capabilities(raw: dict) -> dict[str, CapabilityInfo]:
    result: dict[str, CapabilityInfo] = {}
    caps = raw.get("capabilities", {})
    if not isinstance(caps, dict):
        return result
    for key, value in caps.items():
        if not isinstance(value, dict):
            continue
        endpoints: dict[str, EndpointInfo] = {}
        for ep_key, ep_val in value.get("endpoints", {}).items():
            if not isinstance(ep_val, dict):
                continue
            endpoints[ep_key] = EndpointInfo(
                path=ep_val.get("path", ""),
                method=ep_val.get("method", "POST"),
                providers=list(ep_val.get("providers", [])),
            )
        result[key] = CapabilityInfo(
            description=value.get("description", ""),
            providers=list(value.get("providers", [])),
            endpoints=endpoints,
        )
    return result


def _parse_detect_response(raw: dict) -> DetectResponse:
    frame = raw.get("frame") or raw
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
        for p in frame.get("persons", [])
    ]
    return DetectResponse(
        provider=raw["provider"],
        num_persons=frame.get("num_persons", len(persons)),
        image_width=frame["image_width"],
        image_height=frame["image_height"],
        persons=persons,
        output_path=frame.get("output_path"),
        elapsed_ms=float(raw.get("elapsed_ms", 0.0)),
    )
