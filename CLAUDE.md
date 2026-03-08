# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Goal

**Dance Tracker** is a local dance video analyzer. It processes dance video footage to extract,
annotate, and review movement data — including pose estimation, bounding boxes, segmentation,
and motion sequences — to assist in choreography analysis and performance review.

The application is designed to run locally on hardware with a dedicated GPU (currently targeting
an NVIDIA RTX 3090). Architecture decisions must not prevent future packaging or export.

---

## License Policy

Only libraries with licenses that allow **free use in closed-source commercial applications**
are permitted. Acceptable licenses: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, PSF.

**Prohibited**: GPL, LGPL, AGPL, CC-NC, or any license that requires source disclosure or
restricts commercial use.

Approved detection/pose libraries (accessed only via the external `ImageDetectorsClient` service,
never imported directly into this repo):
- **RT-DETR** — object detection
- **MediaPipe** — detection, pose estimation, segmentation
- **SAM (Meta)** — segmentation
- **MoveNet** — pose estimation

---

## Commands

```bash
# Run the app
make run           # or: python main.py

# Install dependencies (into .venv)
make environment   # or: pip install -r requirements.txt
```

No test runner is configured. No linter is configured.

---

## Configuration

- `preferences/app.env` — app-level settings (`FRAME_CACHE_RADIUS`, `AUDIO_SAMPLE_SECONDS`, `MAX_RECENT_FOLDERS`)
- `preferences/ui.env` — UI settings (`FULLSCREEN`, `TITLE`)
- `preferences/ui.qss` — Qt stylesheet
- `secrets.env` — secrets at repo root (not committed), e.g. `AUDD_API_TOKEN`
- `~/.dance_tracker_prefs.json` — runtime user prefs (recent folders, splitter sizes, last screen)

Config classes use `pydantic-settings` (`BaseSettings`) and load from those env files automatically.

---

## Architecture

The codebase enforces a **strict three-layer separation** with explicit contracts.
No layer may reach across the boundary directly.

```
UI (PySide6)  ──→  DanceTrackerPort (Protocol)  ──→  App (business logic)
App           ──→  EventBus                      ──→  UI (event callbacks)
```

### Core principles

- **UI contains zero business logic.** Presentation only.
- **App is autonomous.** It does not import or reference any Qt symbol.
- **UI → App**: only through `DanceTrackerPort` (and its sub-ports).
- **App → UI**: only through `EventBus` events.
- **Async strategy**:
  - App layer uses `asyncio` (framework-agnostic, no Qt dependency).
  - UI layer uses `QThread` / `QRunnable` for background work; bridges to asyncio via
    a dedicated event loop thread when needed.

### Wiring (`bootstrap/launcher.py`)

1. `DanceTrackerApp` is created with its `Config`.
2. `AppAdapter` wraps the app and implements `DanceTrackerPort` — this is the object the UI calls.
3. `EventBus` carries app → UI events; `MainWindow` is registered as a listener via `bus.connect(wnd)`.
4. `GraphicApp` (PySide6 `QApplication` wrapper) starts the Qt event loop.

### Contracts (`app/interface/`)

- `application.py` — `DanceTrackerPort` and sub-ports: `FramesPort`, `MediaPort`, `MusicPort`,
  `SequencePort`, `SequenceDataPort`, `TrackDetectorPort`
- `event_bus.py` — `EventBus` and `EventsListener` Protocol (what the UI must implement)
- Other files define shared data models used across the boundary

### App layer (`app/track_app/`)

- `main_app.py` — `DanceTrackerApp`: constructs and holds all services
- `adapter.py` — `AppAdapter` and sub-adapters implementing the Port protocols
- `frame_state/logic.py` — `ReviewState`: playback state (current frame, play/pause, error frames)
- `frame_state/layers.py` — Layer/Segment definitions for the timeline
- `sections/` — domain subsystems: `video_manager`, `music_identifier`, `track_detector`
- `services/` — implementations of music identification (audd.io + scipy BPM analysis)

### UI layer (`ui/`)

- `window/main_window.py` — `MainWindow`: thin orchestrator; delegates to section objects
- `window/sections/` — UI sections: `ViewerPanel`, `RightPanel`, `TimelinePanel`, `StatusPanel`,
  `TopBar`, `PlaybackController`, `FolderSessionManager`, `PreferencesManager`
- `widgets/` — reusable widgets
- `window/layout.py` — Qt layout / splitter wiring

### External detection service (`services/image_detectors/`)

- `ImageDetectorsClient`: HTTP client for the external ImageDetectors API.
  Provides pose estimation, bounding boxes, and segmentation. Runs as a separate process.
- All calls are async (asyncio). The app layer consumes this client; the UI never calls it directly.
- Detection libraries (RT-DETR, MediaPipe, SAM, MoveNet) live exclusively in that external service.

---

## Data / File Conventions

**Sidecar metadata** (`.dance_tracker.json`): Created alongside each video after frame extraction.
Stores relative paths to `frames/` and `low_frames/`, video info, and bookmarks.
Bookmarks live under `sequence.bookmarks` as `{frame, name, locked}` objects.
Minimum distance between bookmarks is 25 frames.

**Frame extraction**: A video produces two sibling directories — `frames/` (full-resolution JPGs,
`frame_NNNNNN.jpg`) and `low_frames/` (max 320 px on longest side, used as proxy images during
timeline scrubbing).

**Dropping content**: The app accepts a folder of images, a video file, or a `.dance_tracker.json`
sidecar file. All three paths resolve to a frames folder before emitting `Event.FramesLoaded`.

---

## Code Quality Standards

All code must be **SOLID** and **semantically clear**:

| Principle | Expectation |
|-----------|-------------|
| **S** — Single Responsibility | Each class/module has one reason to change |
| **O** — Open/Closed | Extend via new classes or protocols, not by modifying existing ones |
| **L** — Liskov Substitution | Subtypes are fully substitutable for their base types/protocols |
| **I** — Interface Segregation | Ports are narrow and role-specific (no fat interfaces) |
| **D** — Dependency Inversion | High-level modules depend on abstractions, never on concretions |

Naming must be intention-revealing. Avoid abbreviations, generic names (`manager`, `helper`,
`utils` as a dumping ground), and comments that restate what the code already says.

---

## Conventions

- All source code, comments, commit messages, UI strings, and logs must be in **English**.
- Business logic belongs in `DanceTrackerApp`; UI must not contain business logic.
- UI calls the app through `DanceTrackerPort`; the app notifies the UI through `EventBus`.
- All context menus must subclass `ui/widgets/generic_widgets/context_menu.py`.
- All dialog windows must subclass `ui/widgets/generic_widgets/base_dialog.py`.
- Generic/reusable widgets go in `ui/widgets/generic_widgets/`.

---

## Project Tracking Files

- **`issues.md`** — active issues found during development. Each issue has severity, estimated
  effort, and current status. Consult and update this file when finding or fixing problems.
- **`evaluation.md`** — periodic SOLID and semantic quality evaluation of the codebase.
  Scored 0–10 globally and per class. Includes improvement actions.
