from __future__ import annotations

import cv2
import numpy as np
from scipy import ndimage


def generate_demo_frame(size: int = 320, sigma: float = 2.0) -> np.ndarray:
    """Generate a synthetic grayscale frame and process it."""
    image = np.zeros((size, size), dtype=np.uint8)
    cv2.circle(image, (size // 2, size // 2), size // 4, 255, -1)
    return ndimage.gaussian_filter(image, sigma=sigma)
