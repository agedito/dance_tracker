import sys

from PySide6.QtWidgets import QApplication

from app.config import load_config
from app.layers import default_layers
from app.logic import ReviewState
from ui.window import MainWindow

title = "Frame Review UI (PySide6 mock)"


def launch():
    main_app = QApplication(sys.argv)

    app = ReviewState(total_frames=1200, fps=30, layers=default_layers())
    config = load_config()
    wnd = MainWindow(title, app, config.frame_cache_radius)
    wnd.show()
    sys.exit(main_app.exec())
