from __future__ import annotations

import sys

import matplotlib.pyplot as plt
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

from logic import generate_demo_frame


class DanceTrackerWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Dance Tracker - POC")

        self.status = QLabel("Interfaz lista. Pulsa el botón para ver una detección demo.")
        self.show_demo_button = QPushButton("Mostrar demo de detección")
        self.show_demo_button.clicked.connect(self.show_demo_detection)

        layout = QVBoxLayout()
        layout.addWidget(self.status)
        layout.addWidget(self.show_demo_button)
        self.setLayout(layout)

    def show_demo_detection(self) -> None:
        frame = generate_demo_frame()
        plt.figure("Detección demo")
        plt.imshow(frame, cmap="gray")
        plt.title("Demo OpenCV + NumPy + SciPy")
        plt.axis("off")
        plt.show()


def run_app() -> None:
    app = QApplication(sys.argv)
    window = DanceTrackerWindow()
    window.resize(420, 120)
    window.show()
    app.exec()
