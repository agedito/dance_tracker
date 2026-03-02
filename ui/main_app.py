import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import QApplication

from app.interface.application import DanceTrackerPort
from app.interface.event_bus import EventBus
from ui.config import Config
from ui.window.main_window import MainWindow
from ui.window.sections.preferences_manager import PreferencesManager


class _MainThreadDispatcher(QObject):
    """Routes EventBus callbacks to the Qt main thread.

    When ``dispatch`` is called from a background thread the callable is posted
    to the main thread's event queue via a queued signal connection. When called
    from the main thread it is invoked directly to preserve synchronous semantics.
    """

    _call: Signal = Signal(object)

    def __init__(self):
        super().__init__()
        self._call.connect(self._execute, Qt.ConnectionType.QueuedConnection)

    def dispatch(self, fn: Callable[[], None]) -> None:
        if QThread.currentThread() is self.thread():
            fn()
        else:
            self._call.emit(fn)

    def _execute(self, fn: Callable[[], None]) -> None:
        fn()


class GraphicApp:
    def __init__(self, app: DanceTrackerPort):
        self._app = app
        self._dispatcher: _MainThreadDispatcher | None = None

    def launch(self, cfg: Config, bus: EventBus, prefs: PreferencesManager):
        qt_app = QApplication(sys.argv)

        self._dispatcher = _MainThreadDispatcher()
        bus.set_dispatcher(self._dispatcher.dispatch)

        wnd = MainWindow(cfg, self._app, bus, prefs)
        bus.connect(wnd)

        self._app.sequences.refresh()
        last_folder = self._app.sequences.last_opened_folder()
        if isinstance(last_folder, str) and Path(last_folder).expanduser().is_dir():
            self._app.sequences.load(last_folder)

        sys.exit(qt_app.exec())
