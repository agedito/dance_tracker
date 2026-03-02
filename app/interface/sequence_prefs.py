from typing import Protocol


class SequencePreferencesPort(Protocol):
    """Persistence operations that SequencesAdapter needs from the preferences store.

    Defined in the app layer and implemented by PreferencesManager in the UI layer,
    so SequencesAdapter never touches the preferences file directly.  The UI owns
    the single write handle to the preferences file; the app layer only calls
    this port.
    """

    def recent_folders(self) -> list[str]: ...

    def last_opened_folder(self) -> str | None: ...

    def thumbnail_for_folder(self, folder_path: str) -> str | None: ...

    def register_recent_folder(self, folder_path: str) -> None: ...

    def remove_recent_folder(self, folder_path: str) -> None: ...

    def save_recent_folders_order(self, order: list[str]) -> None: ...
