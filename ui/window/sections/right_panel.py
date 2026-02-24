import math

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout

from ui.widgets.pose_3d_viewer import Pose3DViewerWidget
from ui.widgets.thumbnail import ThumbnailWidget


class RightPanel(QFrame):
    """Single responsibility: display layer thumbnails and 3D pose viewer."""

    def __init__(self):
        super().__init__()
        self.setObjectName("Panel")

        v = QVBoxLayout(self)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(10)

        v.addWidget(self._section_label("LAYER VIEWERS"))
        grid1 = QGridLayout()
        grid1.setSpacing(8)
        grid1.addWidget(self._thumb("Layer 1: Color Grade", 10), 0, 0)
        grid1.addWidget(self._thumb("Layer 1: Output", 17), 0, 1)
        v.addLayout(grid1)

        v.addWidget(self._section_label("LAYER 2: OBJECT MASK"))
        grid2 = QGridLayout()
        grid2.setSpacing(8)
        grid2.addWidget(self._thumb("Layer 2: Mask", 24), 0, 0)
        grid2.addWidget(self._thumb("Layer 2: Overlay", 31), 0, 1)
        v.addLayout(grid2)

        v.addWidget(self._section_label("POSES 3D"))
        self.pose_3d_viewer = Pose3DViewerWidget()
        v.addWidget(self.pose_3d_viewer, 1)

        v.addStretch(1)
        footer = QLabel("Mock: thumbnails procedural + poses YOLO 3D.")
        footer.setObjectName("FooterNote")
        v.addWidget(footer)

    def update_pose(self, frame: int):
        detections = self._mock_yolo_pose_detections(frame)
        self.pose_3d_viewer.set_detections(detections)

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionTitle")
        return label

    @staticmethod
    def _thumb(label: str, seed: int) -> QFrame:
        f = QFrame()
        f.setObjectName("ThumbFrame")
        layout = QVBoxLayout(f)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(ThumbnailWidget(label, seed))
        return f

    @staticmethod
    def _mock_yolo_pose_detections(frame: int) -> list[dict]:
        t = frame * 0.08

        def person(cx: float, arm_offset: float, confidence: float = 0.95):
            kp = [
                [cx, 0.25, confidence],
                [cx - 0.03, 0.24, confidence],
                [cx + 0.03, 0.24, confidence],
                [cx - 0.06, 0.27, confidence],
                [cx + 0.06, 0.27, confidence],
                [cx - 0.10, 0.36, confidence],
                [cx + 0.10, 0.36, confidence],
                [cx - 0.16 - arm_offset, 0.46, confidence],
                [cx + 0.16 + arm_offset, 0.46, confidence],
                [cx - 0.20 - arm_offset, 0.56, confidence],
                [cx + 0.20 + arm_offset, 0.56, confidence],
                [cx - 0.08, 0.60, confidence],
                [cx + 0.08, 0.60, confidence],
                [cx - 0.09, 0.77, confidence],
                [cx + 0.09, 0.77, confidence],
                [cx - 0.09, 0.95, confidence],
                [cx + 0.09, 0.95, confidence],
            ]
            return {"keypoints": kp}

        characters = frame % 3
        if characters == 0:
            return []
        if characters == 1:
            return [person(0.5, 0.04 * math.sin(t))]
        return [
            person(0.36, 0.04 * math.sin(t)),
            person(0.64, 0.04 * math.cos(t + 0.5)),
        ]
