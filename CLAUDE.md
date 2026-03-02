# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app
make run           # or: python main.py

# Install dependencies (into .venv)
make environment   # or: pip install -r requirements.txt
```

No test runner is configured. No linter is configured.

## Configuration

- `preferences/app.env` — app-level settings (`FRAME_CACHE_RADIUS`, `AUDIO_SAMPLE_SECONDS`, `MAX_RECENT_FOLDERS`)
- `preferences/ui.env` — UI settings (`FULLSCREEN`, `TITLE`)
- `preferences/ui.qss` — Qt stylesheet
- `secrets.env` — secrets at repo root (not committed), e.g. `AUDD_API_TOKEN`
- `~/.dance_tracker_prefs.json` — runtime user prefs (recent folders, splitter sizes, last screen)

Config classes use `pydantic-settings` (`BaseSettings`) and load from those env files automatically.

## Architecture

The codebase enforces a strict three-layer separation with explicit contracts:

```
UI (PySide6)  ──→  DanceTrackerPort (Protocol)  ──→  App (business logic)
App           ──→  EventBus                      ──→  UI (event callbacks)
```

**Wiring** (`bootstrap/launcher.py`):
1. `DanceTrackerApp` is created with its `Config`.
2. `AppAdapter` wraps the app and implements `DanceTrackerPort` — this is the object the UI calls.
3. `EventBus` carries app → UI events; `MainWindow` is registered as a listener via `bus.connect(wnd)`.
4. `GraphicApp` (PySide6 `QApplication` wrapper) starts the Qt event loop.

**Contracts** (`app/interface/`):
- `application.py` — `DanceTrackerPort` (what the UI can call) and sub-ports: `FramesPort`, `MediaPort`, `MusicPort`, `SequencePort`, `SequenceDataPort`, `TrackDetectorPort`
- `event_bus.py` — `EventBus` and `EventsListener` Protocol (what the UI must implement to receive events)
- Other files define shared data models used across the boundary

**App layer** (`app/track_app/`):
- `main_app.py` — `DanceTrackerApp`: constructs and holds all services
- `adapter.py` — `AppAdapter` and sub-adapters implementing the Port protocols
- `frame_state/logic.py` — `ReviewState`: playback state (current frame, play/pause, error frames)
- `frame_state/layers.py` — Layer/Segment definitions for the timeline
- `sections/` — domain subsystems: `video_manager`, `music_identifier`, `track_detector`
- `services/` — implementations of music identification (audd.io + scipy BPM analysis)

**UI layer** (`ui/`):
- `window/main_window.py` — `MainWindow`: thin orchestrator; delegates to section objects
- `window/sections/` — UI sections: `ViewerPanel`, `RightPanel`, `TimelinePanel`, `StatusPanel`, `TopBar`, `PlaybackController`, `FolderSessionManager`, `PreferencesManager`
- `widgets/` — reusable widgets
- `window/layout.py` — Qt layout / splitter wiring

**External service** (`services/mediapipe/`):
- `MPVisionClient`: HTTP client for an external MPVision API (pose, bbox, segmentation). Runs separately.

## Data / File Conventions

**Sidecar metadata** (`.dance_tracker.json`): Created alongside each video after frame extraction. Stores relative paths to `frames/` and `low_frames/`, video info, and bookmarks. Bookmarks live under `sequence.bookmarks` as `{frame, name, locked}` objects. Minimum distance between bookmarks is 25 frames.

**Frame extraction**: A video produces two sibling directories — `frames/` (full-resolution JPGs, frame_NNNNNN.jpg) and `low_frames/` (max 320px on longest side, used as proxy images during timeline scrubbing).

**Dropping content**: The app accepts a folder of images, a video file, or a `.dance_tracker.json` sidecar file. All three paths resolve to a frames folder before emitting `Event.FramesLoaded`.

## Conventions (from AGENTS.md)

- All source code, comments, commit messages, UI strings, and logs must be in **English**.
- Business logic belongs in `DanceTrackerApp`; UI must not contain business logic.
- UI calls the app through `DanceTrackerPort`; the app notifies the UI through `EventBus`.
- All context menus must subclass `ui/widgets/generic_widgets/context_menu.py`.
- All dialog windows must subclass `ui/widgets/generic_widgets/base_dialog.py`.
- Generic/reusable widgets go in `ui/widgets/generic_widgets/`.
