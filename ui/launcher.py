import sys

from PySide6.QtWidgets import QApplication

from app.layers import default_layers
from app.logic import ReviewState
from bootstrap.config import AppConfig
from ui.window import MainWindow

title = "Frame Review UI (PySide6 mock)"


def launch(cfg: AppConfig):
    main_app = QApplication(sys.argv)

    app = ReviewState(total_frames=1200, fps=30, layers=default_layers(), config=cfg)
    wnd = MainWindow(title, app)
    wnd.showFullScreen()
    sys.exit(main_app.exec())
