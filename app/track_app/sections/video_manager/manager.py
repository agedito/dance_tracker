from pathlib import Path

import cv2

VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}
VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


class VideoManager:
    @staticmethod
    def is_video(video_path: str) -> bool:
        source = Path(video_path)
        if not source.exists() or not source.is_file():
            return False

        if source.suffix.lower() not in VIDEO_SUFFIXES:
            return False

        return True

    def extract_frames(self, video_path: str) -> str | None:
        source = Path(video_path)
        if not self.is_video(video_path):
            return None

        frames_dir = source.parent / "frames"
        frames_mino_dir = source.parent / "frames_mino"
        if frames_dir.exists():
            return str(frames_dir)

        frames_dir.mkdir(parents=True, exist_ok=True)
        frames_mino_dir.mkdir(parents=True, exist_ok=True)

        for output_dir in (frames_dir, frames_mino_dir):
            for item in output_dir.iterdir():
                if item.is_file() and item.suffix.lower() in VALID_SUFFIXES:
                    item.unlink()

        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            return None

        frame_idx = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            out_name = f"frame_{frame_idx:06d}.jpg"
            cv2.imwrite(str(frames_dir / out_name), frame)

            h, w = frame.shape[:2]
            max_dim = max(w, h)
            scale = 1.0 if max_dim <= 320 else 320.0 / max_dim
            scaled_w = max(1, int(round(w * scale)))
            scaled_h = max(1, int(round(h * scale)))
            resized = cv2.resize(frame, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(frames_mino_dir / out_name), resized)

            frame_idx += 1

        capture.release()

        if frame_idx == 0:
            return None

        print("Finished")
        return str(frames_dir)
