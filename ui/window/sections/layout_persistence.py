from PySide6.QtWidgets import QApplication, QMainWindow

from ui.window.layout import MainWindowLayout
from ui.window.sections.preferences_manager import PreferencesManager


class LayoutPersistence:
    """Saves and restores splitter sizes and the window's screen assignment."""

    _SPLITTER_NAMES = ("top_splitter", "bottom_splitter", "main_splitter")

    def __init__(self, layout: MainWindowLayout, prefs: PreferencesManager, window: QMainWindow):
        self._layout = layout
        self._prefs = prefs
        self._window = window

    def restore(self) -> None:
        self._restore_screen()
        self._window.showFullScreen()
        for name in self._SPLITTER_NAMES:
            sizes = self._prefs.splitter_sizes(name)
            if sizes:
                getattr(self._layout, name).setSizes(sizes)

    def connect_save_on_move(self) -> None:
        for name in self._SPLITTER_NAMES:
            getattr(self._layout, name).splitterMoved.connect(self.save)

    def save(self, *_) -> None:
        self._prefs.save_fullscreen(self._window.isFullScreen())
        for name in self._SPLITTER_NAMES:
            self._prefs.save_splitter_sizes(name, getattr(self._layout, name).sizes())
        self._prefs.save()

    def save_screen(self) -> None:
        current_screen = self._window.windowHandle().screen() if self._window.windowHandle() else None
        self._prefs.save_last_screen_name(current_screen.name() if current_screen else None)

    def _restore_screen(self) -> None:
        screen_name = self._prefs.last_screen_name()
        if not screen_name:
            return
        for screen in QApplication.screens():
            if screen.name() == screen_name:
                self._window.setGeometry(screen.availableGeometry())
                return
