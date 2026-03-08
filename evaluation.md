# Code Quality Evaluation

Periodic SOLID and semantic quality evaluation of the Dance Tracker codebase.
Scores range from **0** (does not meet the criterion at all) to **10** (exemplary).

Update this file after significant refactors or when explicitly requested.

---

## Scoring Criteria

### SOLID dimensions
| ID | Principle | What a 10 looks like |
|----|-----------|----------------------|
| S | Single Responsibility | Every class/module has exactly one reason to change |
| O | Open/Closed | New behavior is added via extension, never by editing stable code |
| L | Liskov Substitution | All protocol/base implementations are fully interchangeable |
| I | Interface Segregation | All ports are narrow; no client is forced to depend on methods it does not use |
| D | Dependency Inversion | All cross-layer dependencies point to abstractions (Protocols/ABCs) |

### Semantic dimensions
| ID | Dimension | What a 10 looks like |
|----|-----------|----------------------|
| N | Naming | Every name reveals intent; no abbreviations or misleading terms |
| C | Cohesion | Related behavior lives together; unrelated behavior is separated |
| A | Abstraction level | Each unit operates at a single level of abstraction |
| R | Readability | Code reads like prose; comments explain *why*, not *what* |

---

## Global Score — `app/` layer · 2026-03-08

| S | O | L | I | D | N | C | A | R | **Overall** |
|---|---|---|---|---|---|---|---|---|-------------|
| 8.7 | 7.4 | 8.8 | 9.2 | 8.6 | 9.2 | 8.4 | 8.6 | 8.5 | **8.6** |

**Summary:** The interface/contract layer is outstanding. Weak spots are concentrated in
`DanceTrackerApp` (god object), `FrameStore` (Qt coupling + threading complexity), and
a handful of overlong methods.

---

## Per-Class / Per-Module Evaluation · 2026-03-08

---

#### `app/interface/application.py` — `FramesPort`, `DanceTrackerPort`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 9 | Protocols define single, focused contracts |
| O | 9 | Protocol-based; swap implementations without touching contract |
| L | 10 | Any conforming implementation is fully substitutable |
| I | 10 | Sub-ports are narrow and role-specific |
| D | 10 | High-level modules depend only on Protocol abstractions |
| N | 10 | Clear, intent-revealing names |
| C | 10 | Cohesive protocol definitions grouped logically |
| A | 10 | Operates at the correct abstraction level (contract definition) |
| R | 10 | Clean definitions with no clutter |
| **Overall** | **9.8** | |

**Improvement actions**
- None required.

---

#### `app/interface/event_bus.py` — `Event`, `EventsListener`, `EventBus`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 9 | Each class has one responsibility; EventBus dispatches, Event enumerates |
| O | 9 | New events extend the enum; listeners extend the protocol |
| L | 10 | EventsListener protocol enforces substitutability |
| I | 10 | Listener interface has one method per event; no fat interface |
| D | 10 | EventBus depends on Protocol; custom dispatchers injectable via `set_dispatcher` |
| N | 9 | Clear names throughout |
| C | 9 | Coherent event bus with thread safety |
| A | 9 | Correct abstraction level |
| R | 8 | Deferred-event re-entrancy logic is complex; comments help but the mechanism is non-obvious |
| **Overall** | **9.2** | |

**Improvement actions**
- [ ] Add a short inline explanation of *why* deferred events are needed (re-entrancy scenario).

---

#### `app/interface/events.py` — `AppEvents`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 8 | Pure data container, but mutable lambda default is an anti-pattern |
| O | 5 | Adding new events requires modifying the dataclass |
| L | 9 | Substitutable, though not used polymorphically |
| I | 8 | Minimal, but dataclass format is unusual for event definitions |
| D | 6 | Direct dependency on concrete `Callable` type |
| N | 7 | `AppEvents` is generic; individual callback names are clear |
| C | 8 | Single container cohesion |
| A | 7 | Appropriate, but mixing data with callable defaults is a level mismatch |
| R | 7 | Mutable default lambdas obscure intent |
| **Overall** | **7.4** | |

**Improvement actions**
- [ ] Replace mutable lambda defaults with `field(default=None)` + explicit None checks or a factory.
- [ ] Consider whether `AppEvents` is still needed alongside `EventBus`; evaluate merging.

---

#### `app/interface/layers.py` — `Segment`, `Layer`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 10 | Pure data classes; one responsibility each |
| O | 6 | Frozen dataclasses cannot be structurally extended |
| L | 10 | Fully substitutable immutable values |
| I | 10 | Minimal, no bloat |
| D | 9 | No concrete dependencies |
| N | 10 | Clear names |
| C | 10 | Tightly cohesive |
| A | 10 | Correct data-model level |
| R | 10 | Simple and readable |
| **Overall** | **9.2** | |

**Improvement actions**
- None required.

---

#### `app/interface/` — remaining Protocol files (`media.py`, `music.py`, `sequences.py`, `sequence_data.py`, `sequence_prefs.py`, `track_detector.py`)
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 10 | Each protocol has one responsibility |
| O | 9 | Implementations extend without touching contracts |
| L | 10 | Guaranteed by Protocol |
| I | 10 | Role-specific, narrow interfaces |
| D | 10 | All consumers depend on abstractions |
| N | 10 | Intent-revealing names (`MediaPort`, `SongMetadata`, etc.) |
| C | 10 | Cohesive grouping |
| A | 10 | Correct abstraction level |
| R | 10 | Clean, readable |
| **Overall** | **9.8** | |

**Improvement actions**
- None required.

---

#### `app/track_app/main_app.py` — `DanceTrackerApp`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 6 | Constructs and holds ReviewState, VideoManager, MusicIdentifier, TrackDetector — multiple unrelated responsibilities |
| O | 5 | New services require modifying `__init__`; no extension point |
| L | 8 | Usable polymorphically via its public interface |
| I | 5 | Wide surface exposes many unrelated services |
| D | 7 | Depends on concrete implementations (e.g. `MusicIdentifierService` directly) |
| N | 9 | Names are clear |
| C | 4 | Mixes state management, video extraction, music identification, detection logic |
| A | 5 | Mixes initialization, service aggregation, and state holding |
| R | 7 | Readable constructor, but the class is doing too much |
| **Overall** | **6.4** | |

**Improvement actions**
- [ ] (**ISSUE-001**) Extract a `ServiceFactory` or dedicated builder. Break `DanceTrackerApp` into focused components (e.g. `PlaybackManager`, `MetadataManager`).
- [ ] Move the module-level `_load_detection_api_detectors` function into a proper factory/builder class.
- [ ] Introduce constructor injection so each service receives its dependencies explicitly.

---

#### `app/track_app/config.py` — `Config`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 10 | Single responsibility: configuration loading |
| O | 8 | Immutable, but adding fields requires modification |
| L | 9 | Valid settings object |
| I | 7 | Audio, detection, and frame settings mixed together |
| D | 9 | Uses pydantic `BaseSettings` (abstract configuration source) |
| N | 8 | Clear, though some names are verbose |
| C | 6 | Grab-bag of unrelated settings |
| A | 8 | Appropriate config level |
| R | 9 | Clear definitions with sensible defaults |
| **Overall** | **8.1** | |

**Improvement actions**
- [ ] Group settings into nested config objects (`AudioConfig`, `DetectionConfig`, `FrameConfig`).

---

#### `app/track_app/adapter.py` — `MediaAdapter`, `MusicAdapter`, `SequencesAdapter`, `FramesAdapter`, `SequenceDataAdapter`, `TrackDetectorAdapter`, `AppAdapter`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 7 | `MediaAdapter` mixes path resolution + event emission; `SequencesAdapter` mixes preference bridging + event emission |
| O | 8 | Mostly closed; new behavior requires modification |
| L | 9 | All adapters implement protocols correctly |
| I | 9 | Segregated by domain (Media, Music, Sequences, etc.) |
| D | 8 | Depend on app layer and interfaces |
| N | 9 | Clear adapter names |
| C | 7 | `MediaAdapter` mixes orchestration levels |
| A | 7 | `MediaAdapter.load` mixes high-level orchestration with low-level path resolution |
| R | 7 | Some methods are long (path resolution in `MediaAdapter`) |
| **Overall** | **8.0** | |

**Improvement actions**
- [ ] (**ISSUE-006**) Extract `MediaAdapter._resolve_input_path()` to a dedicated `InputPathResolver` class.
- [ ] Split event emission from business logic within adapters.

---

#### `app/track_app/frame_state/logic.py` — `ReviewState`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 9 | Single responsibility: playback state (frame, play/pause, layers, error frames) |
| O | 7 | Logic is tightly coupled to internal state; extending requires subclassing |
| L | 8 | Substitutable for playback state management |
| I | 9 | Focused public interface |
| D | 8 | Depends on `Config` (concrete), not other services |
| N | 9 | Clear method names (`play`, `pause`, `set_frame`, `next_error_frame`) |
| C | 9 | Highly cohesive state management |
| A | 9 | Correct abstraction level |
| R | 9 | Readable, straightforward logic |
| **Overall** | **8.6** | |

**Improvement actions**
- [ ] Introduce a `PlaybackStatePort` Protocol so `ReviewState` can be replaced/mocked in tests.

---

#### `app/track_app/frame_state/frame_store.py` — `FrameStore`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 7 | Manages frame loading, caching, and preloading — three concerns in one class |
| O | 6 | Tightly coupled to Qt; difficult to extend without modification |
| L | 6 | Inherits from `QObject`; not strongly polymorphic |
| I | 6 | Public interface is wide; several internal helpers exposed |
| D | 6 | Direct dependency on Qt (`QObject`, `QPixmap`, `Signal`) |
| N | 8 | Names are generally clear (`cache_radius`, `preload_thread`, etc.) |
| C | 5 | Caching, threading, preloading, and image I/O are all mixed |
| A | 6 | Mixes Qt signals, threading primitives, caching, and file I/O |
| R | 6 | Preloading + re-entrancy guard logic is hard to follow |
| **Overall** | **6.3** | |

**Improvement actions**
- [ ] (**ISSUE-003**) Extract a `FrameCacheService` that does not inherit from `QObject`. Use a `FrameLoadedListener` Protocol or callback system instead of Qt signals.
- [ ] Extract threading/preload scheduling into a `PreloadScheduler` class using `Queue`/`ThreadPool`.
- [ ] Separate cache read/write from preload coordination.

---

#### `app/track_app/frame_state/layers.py` — module-level `default_layers()`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 10 | Single responsibility: default layer configuration |
| O | 5 | Hard-coded layer data; extending requires code modification |
| L | 10 | Returns correct immutable data |
| I | 10 | Single function interface |
| D | 9 | Returns abstract `Layer` types |
| N | 9 | `default_layers()` is clear |
| C | 9 | Cohesive configuration |
| A | 10 | Correct level |
| R | 10 | Simple, readable |
| **Overall** | **8.8** | |

**Improvement actions**
- [ ] Load layer definitions from config or a data file to avoid hardcoding.

---

#### `app/track_app/sections/video_manager/manager.py` — `VideoManager`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 9 | Single responsibility: extract frames from video + compute metadata |
| O | 8 | Could extend via subclassing; cv2 coupling is hard-coded |
| L | 8 | Consistent public interface |
| I | 9 | Focused interface (`is_video`, `extract_frames`) |
| D | 6 | Direct dependency on `cv2` (concrete) |
| N | 9 | Clear names |
| C | 9 | Cohesive frame extraction |
| A | 9 | Correct abstraction level |
| R | 8 | Readable, but `extract_frames` is 90+ lines with nested loops |
| **Overall** | **8.4** | |

**Improvement actions**
- [ ] (**ISSUE-002**) Break `extract_frames()` (90+ lines) into `_extract_single_frame()`, `_handle_progress()`, and a `CancellationToken` helper.
- [ ] Abstract `cv2` behind a `VideoReaderPort` to allow swapping the backend.

---

#### `app/track_app/sections/video_manager/sequence_data_service.py` — `SequenceDataService`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 8 | Manages video metadata and bookmarks; minor mixing of file I/O + domain logic |
| O | 7 | Can extend via inheritance; some methods could be more composable |
| L | 8 | Properly implements `SequenceDataPort` |
| I | 9 | Focused interface matching the port |
| D | 8 | Depends on abstractions (`sequence_file_store`, `bookmark_domain`) |
| N | 9 | Method names are clear and descriptive |
| C | 8 | Bookmark and video data logic somewhat separated |
| A | 8 | Correct level |
| R | 8 | Readable, but bookmark update operations repeat the same pattern |
| **Overall** | **8.1** | |

**Improvement actions**
- [ ] (**ISSUE-005**) Introduce a generic `apply_bookmark_transformation(updater_fn)` to DRY up `add_bookmark`, `move_bookmark`, `remove_bookmark`, `set_bookmark_name`, `set_bookmark_locked`.

---

#### `app/track_app/sections/video_manager/sequence_metadata_store.py` — `SequenceMetadataStore`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 10 | Single responsibility: JSON metadata I/O |
| O | 8 | Extensible via subclassing; JSON format is locked |
| L | 9 | Properly substitutable |
| I | 10 | Clean, focused interface |
| D | 9 | Depends on abstract `Path` |
| N | 10 | Clear method names |
| C | 10 | Cohesive metadata management |
| A | 10 | Correct level |
| R | 9 | Readable, clear I/O operations |
| **Overall** | **9.3** | |

**Improvement actions**
- None required.

---

#### `app/track_app/sections/video_manager/sequence_file_store.py` — module-level functions
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 10 | Each function has one responsibility |
| O | 7 | Hard-coded path resolution; extending requires modification |
| L | 10 | Pure, composable functions |
| I | 10 | Focused, narrow interface |
| D | 9 | No concrete type dependencies |
| N | 10 | Clear function names |
| C | 9 | Cohesive file/path operations |
| A | 10 | Correct level |
| R | 9 | Readable pure functions |
| **Overall** | **9.1** | |

**Improvement actions**
- None required.

---

#### `app/track_app/sections/video_manager/bookmark_domain.py` — module-level functions
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 10 | Each function is pure domain logic |
| O | 7 | `MIN_BOOKMARK_DISTANCE_FRAMES = 25` hard-coded |
| L | 10 | Pure functions; fully composable |
| I | 10 | Focused, minimal |
| D | 10 | No concrete type dependencies |
| N | 9 | Clear names; `MIN_BOOKMARK_DISTANCE_FRAMES` constant is good |
| C | 10 | Cohesive bookmark business logic |
| A | 10 | Correct domain level |
| R | 9 | Readable; move resolution logic is complex but well-named |
| **Overall** | **9.3** | |

**Improvement actions**
- [ ] (**ISSUE-008**) Move `MIN_BOOKMARK_DISTANCE_FRAMES` to `Config` and pass as parameter.

---

#### `app/track_app/sections/music_identifier/` — `MusicIdentifierService`, `AuddSongIdentifier`, `AudioExtractor`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 9 | Each class has one responsibility |
| O | 7–8 | ffmpeg command and audd URL hard-coded; extend via subclassing |
| L | 9 | Properly implement their ports |
| I | 9 | Focused interfaces |
| D | 8–10 | Service depends on ports; clients have minor concrete deps (subprocess, urllib) |
| N | 9–10 | Clear names throughout |
| C | 9 | Cohesive orchestration/extraction/identification |
| A | 9 | Correct abstraction levels |
| R | 8–9 | Readable; fallback logic (ffmpeg discovery) is clear |
| **Overall** | **8.7** | |

**Improvement actions**
- [ ] (**ISSUE-011**) Replace broad `except Exception` with specific exception types + logging.

---

#### `app/track_app/sections/track_detector/service.py` — `TrackDetectorService`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 7 | Manages detector selection, detection execution, and persistence |
| O | 6 | Tightly coupled to `DetectionsStore` and frame file discovery logic |
| L | 8 | Properly implements `TrackDetectorPort` |
| I | 8 | Focused public interface |
| D | 7 | Depends on `PersonDetector` protocol (good); `DetectionsStore` is concrete |
| N | 8 | Clear names |
| C | 6 | Mixes detection, file I/O, detector switching, and storage |
| A | 6 | Spans multiple abstraction levels within single methods |
| R | 7 | `detect_people_for_sequence` is 65+ lines with nested conditionals |
| **Overall** | **7.1** | |

**Improvement actions**
- [ ] (**ISSUE-004**) Extract single-frame detection to `_detect_single_frame()` and batch to `_detect_batch()`. Consider a `DetectionStrategy` pattern.
- [ ] Abstract `DetectionsStore` behind a `DetectionsPersistencePort`.
- [ ] Share `_VALID_SUFFIXES` with `VideoManager` (DRY).

---

#### `app/track_app/sections/track_detector/detections_store.py` — `DetectionsStore`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 10 | Single responsibility: JSON detections I/O |
| O | 8 | Extensible; JSON format locked |
| L | 9 | Properly substitutable |
| I | 10 | Focused interface |
| D | 9 | Depends on abstract data types (`PersonDetection`) |
| N | 10 | Clear method names |
| C | 10 | Cohesive storage logic |
| A | 10 | Correct level |
| R | 8 | Readable; `_from_dict` validation is verbose but defensively correct |
| **Overall** | **9.1** | |

**Improvement actions**
- [ ] Extract `_from_dict` parsing to a dedicated `PersonDetectionParser` if it grows further.

---

#### `app/track_app/sections/track_detector/detection_api_adapter.py` — `DetectionApiPersonDetector`
#### `app/track_app/sections/track_detector/mpvision_adapter.py` — `MPVisionPersonDetector`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 8–9 | Single responsibility (detect via external API) |
| O | 6 | Hard-coded thresholds; extends via subclassing only |
| L | 8–9 | Properly implement `PersonDetector` |
| I | 8–9 | Focused interface |
| D | 8 | Client is injected; thresholds are constructor params but magic numbers |
| N | 8–9 | Clear naming |
| C | 7–9 | API calls + response mapping together |
| A | 8–9 | Correct level |
| R | 8–9 | Readable |
| **Overall** | **7.8 / 8.5** | |

**Improvement actions**
- [ ] (**ISSUE-009**) Move threshold defaults to `Config` / environment variables.
- [ ] Extract response-to-domain mapping into a separate mapper function.

---

#### `app/track_app/sections/track_detector/mock_detectors.py` — `MockPersonDetector`, `NearbyMockPersonDetector`
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 8 | Each detector generates mock detections; geometry helpers are pure |
| O | 7 | Hard-coded geometric ratios |
| L | 9 | Properly implement `PersonDetector` |
| I | 9 | Focused interface |
| D | 10 | No concrete type dependencies; pure geometry |
| N | 9 | Clear names (`random_box`, `jitter_box`, `_image_size`) |
| C | 8 | Cohesive mock logic |
| A | 9 | Correct level |
| R | 8 | Geometry helpers are well-named; binary image parsing is clever but fragile |
| **Overall** | **8.6** | |

**Improvement actions**
- [ ] (**ISSUE-010**) Replace binary image header parsing in `_image_size()` with PIL/Pillow (already a dependency).

---

#### `app/track_app/services/music_identifier/` — `MusicIdentifierService`, `AuddSongIdentifier`, `AudioExtractor`, `ScipyTempoAnalyzer`, ports
| Criterion | Score | Notes |
|-----------|-------|-------|
| S | 9–10 | Each class has one focused responsibility |
| O | 7–8 | ffmpeg and audd URL hard-coded; DSP window params hard-coded |
| L | 9 | All implement their ports correctly |
| I | 9–10 | Focused, role-specific interfaces |
| D | 8–10 | Service depends on port abstractions; scipy/ffmpeg are concrete in leaf classes |
| N | 9–10 | Intent-revealing names throughout |
| C | 9 | Cohesive per class |
| A | 9 | Correct levels |
| R | 8–9 | Readable; DSP variable names are descriptive |
| **Overall** | **8.9** | |

**Improvement actions**
- [ ] (**ISSUE-011**) Replace broad `except Exception` with specific types + structured logging.
- [ ] (**ISSUE-012**) Remove duplicate `models.py` re-export file (sections vs services copy).

---

## Evaluation History

| Date | Scope | Overall | Notes |
|------|-------|---------|-------|
| 2026-03-08 | `app/` full layer | **8.6** | First evaluation |
