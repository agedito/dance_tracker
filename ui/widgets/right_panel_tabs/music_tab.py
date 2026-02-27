from collections.abc import Callable

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from app.interface.music import SongMetadata
from ui.widgets.right_panel_tabs.common import section_label


class MusicTabWidget(QWidget):
    def __init__(
        self,
        analyze_music: Callable[[str], SongMetadata],
        get_current_folder: Callable[[], str | None],
    ):
        super().__init__()
        self._analyze_music = analyze_music
        self._get_current_folder = get_current_folder

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(section_label("Music"))

        self._analyze_button = QPushButton("Extract and analyze song")
        self._analyze_button.clicked.connect(self._on_analyze_clicked)
        layout.addWidget(self._analyze_button)

        self._status_value = QLabel("not_run")
        self._title_value = QLabel("—")
        self._artist_value = QLabel("—")
        self._album_value = QLabel("—")
        self._provider_value = QLabel("—")
        self._tempo_value = QLabel("—")
        self._pulses_value = QLabel("—")
        self._duration_value = QLabel("—")
        self._analysis_provider_value = QLabel("—")
        self._message_value = QLabel("")
        self._message_value.setWordWrap(True)

        for label, value in (
            ("Status", self._status_value),
            ("Title", self._title_value),
            ("Artist", self._artist_value),
            ("Album", self._album_value),
            ("Provider", self._provider_value),
            ("Tempo (BPM)", self._tempo_value),
            ("Pulse count", self._pulses_value),
            ("Audio duration", self._duration_value),
            ("Analysis provider", self._analysis_provider_value),
        ):
            layout.addWidget(QLabel(f"{label}:"))
            layout.addWidget(value)

        layout.addWidget(self._message_value)
        layout.addStretch(1)

    def _on_analyze_clicked(self) -> None:
        folder = self._get_current_folder()
        if not folder:
            self._message_value.setText("Load a sequence first to analyze its music.")
            return

        self._analyze_music(folder)

    def update_song_info(self, song: SongMetadata):
        self._status_value.setText(song.status)
        self._title_value.setText(song.title or "—")
        self._artist_value.setText(song.artist or "—")
        self._album_value.setText(song.album or "—")
        self._provider_value.setText(song.provider or "—")
        self._tempo_value.setText(f"{song.tempo_bpm:.1f}" if song.tempo_bpm is not None else "—")
        self._pulses_value.setText(str(song.pulse_count) if song.pulse_count is not None else "—")
        self._duration_value.setText(f"{song.audio_duration_s:.1f} s" if song.audio_duration_s is not None else "—")
        self._analysis_provider_value.setText(song.analysis_provider or "—")
        self._message_value.setText(song.message or "")
