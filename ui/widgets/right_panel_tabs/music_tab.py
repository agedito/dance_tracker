from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.interface.music import SongMetadata
from ui.widgets.right_panel_tabs.common import section_label


class MusicTabWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(section_label("Music"))

        self._status_value = QLabel("not_run")
        self._title_value = QLabel("—")
        self._artist_value = QLabel("—")
        self._album_value = QLabel("—")
        self._provider_value = QLabel("—")
        self._message_value = QLabel("")
        self._message_value.setWordWrap(True)

        for label, value in (
            ("Status", self._status_value),
            ("Title", self._title_value),
            ("Artist", self._artist_value),
            ("Album", self._album_value),
            ("Provider", self._provider_value),
        ):
            layout.addWidget(QLabel(f"{label}:"))
            layout.addWidget(value)

        layout.addWidget(self._message_value)
        layout.addStretch(1)

    def update_song_info(self, song: SongMetadata):
        self._status_value.setText(song.status)
        self._title_value.setText(song.title or "—")
        self._artist_value.setText(song.artist or "—")
        self._album_value.setText(song.album or "—")
        self._provider_value.setText(song.provider or "—")
        self._message_value.setText(song.message or "")
