import cv2
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt


def demo() -> None:
    image = np.zeros((200, 200), dtype=np.uint8)
    cv2.circle(image, (100, 100), 50, 255, -1)
    blurred = ndimage.gaussian_filter(image, sigma=2)

    plt.imshow(blurred, cmap="gray")
    plt.title("Demo OpenCV + NumPy + SciPy + Matplotlib")
    plt.axis("off")
    plt.show()


if __name__ == "__main__":
    demo()
