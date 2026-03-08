from typing import List

from app.interface.layers import Layer, Segment

__all__ = ["Layer", "Segment", "default_layers"]


def default_layers() -> List[Layer]:
    return [
        Layer("Image", [], kind="image"),
        Layer("Bounding Box", [], kind="bbox"),
        Layer("Pose", [], kind="pose"),
        Layer("Segmentation", [], kind="segmentation"),
    ]
