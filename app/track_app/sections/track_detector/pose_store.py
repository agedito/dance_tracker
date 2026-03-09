import json
from pathlib import Path

from app.interface.pose_detector import PoseDetection, PoseLandmark


class PoseStore:
    """Single responsibility: read and write poses.json for a frames folder."""

    @staticmethod
    def json_path(frames_folder_path: str) -> Path:
        return Path(frames_folder_path).expanduser().parent / "poses.json"

    @staticmethod
    def write(
        frames_folder_path: str,
        provider: str,
        poses: dict[int, list[PoseDetection]],
    ) -> None:
        payload = {
            "provider": provider,
            "frames": {
                str(idx): [
                    {"landmarks": [
                        {
                            "index": lm.index,
                            "name": lm.name,
                            "x": lm.x,
                            "y": lm.y,
                            "z": lm.z,
                            "visibility": lm.visibility,
                        }
                        for lm in pose.landmarks
                    ]}
                    for pose in frame_poses
                ]
                for idx, frame_poses in poses.items()
            },
        }
        PoseStore.json_path(frames_folder_path).write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    @staticmethod
    def read(frames_folder_path: str) -> tuple[dict[int, list[PoseDetection]], str | None]:
        path = PoseStore.json_path(frames_folder_path)
        if not path.exists():
            return {}, None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}, None

        if not isinstance(payload, dict):
            return {}, None

        provider = payload.get("provider")
        saved_provider = provider if isinstance(provider, str) else None

        frames_data = payload.get("frames")
        if not isinstance(frames_data, dict):
            return {}, saved_provider

        result: dict[int, list[PoseDetection]] = {}
        for key, items in frames_data.items():
            if not isinstance(key, str) or not key.isdigit() or not isinstance(items, list):
                continue
            frame_poses: list[PoseDetection] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                pose = _parse_pose(item)
                if pose is not None:
                    frame_poses.append(pose)
            result[int(key)] = frame_poses

        return result, saved_provider


def _parse_pose(data: dict) -> PoseDetection | None:
    raw = data.get("landmarks")
    if not isinstance(raw, list):
        return None
    landmarks: list[PoseLandmark] = []
    for lm in raw:
        if not isinstance(lm, dict):
            continue
        try:
            landmarks.append(PoseLandmark(
                index=int(lm["index"]),
                name=str(lm.get("name", "")),
                x=float(lm["x"]),
                y=float(lm["y"]),
                z=float(lm.get("z", 0.0)),
                visibility=float(lm.get("visibility", 1.0)),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    if not landmarks:
        return None
    return PoseDetection(landmarks=tuple(landmarks))
