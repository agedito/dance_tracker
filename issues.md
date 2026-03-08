# Issues

Active issues found during development of Dance Tracker.
Update this file when discovering or resolving problems.

## Severity scale
| Level | Meaning |
|-------|---------|
| **Critical** | Crash, data loss, or security risk |
| **High** | Major feature broken or incorrect behavior visible to the user |
| **Medium** | Degraded experience, workaround exists |
| **Low** | Minor annoyance, cosmetic, or edge case |

## Effort scale
| Label | Estimated time |
|-------|----------------|
| **XS** | < 1 h |
| **S** | 1–3 h |
| **M** | 3–8 h |
| **L** | 1–3 days |
| **XL** | > 3 days |

## Status values
`open` · `in-progress` · `resolved` · `wont-fix`

---

## Open Issues

---

### ISSUE-001 — God object: `DanceTrackerApp` acts as factory and service locator
| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **Effort** | L |
| **Status** | open |
| **File(s)** | `app/track_app/main_app.py` |
| **Class(es)** | `DanceTrackerApp` |

**Description**
`DanceTrackerApp.__init__` constructs and holds all unrelated services (`ReviewState`,
`VideoManager`, `MusicIdentifier`, `TrackDetector`, `SequenceMetadataStore`). The class
is both a factory and a service locator, violating SRP (S: 6/10, C: 4/10).
Makes unit testing impossible without instantiating the entire application.
The module-level helper `_load_detection_api_detectors` is a symptom of the same problem.

**Proposed fix**
Extract a dedicated `AppServiceFactory` or use constructor injection.
Break `DanceTrackerApp` into focused managers (`PlaybackManager`, `MetadataManager`, etc.).
Move `_load_detection_api_detectors` into the factory class.

---

### ISSUE-002 — Method too long: `VideoManager.extract_frames()` (90+ lines)
| Field | Value |
|-------|-------|
| **Severity** | High |
| **Effort** | M |
| **Status** | open |
| **File(s)** | `app/track_app/sections/video_manager/manager.py` |
| **Class(es)** | `VideoManager` |

**Description**
`extract_frames()` handles frame extraction, progress callbacks, cancellation, frame scaling,
and metadata computation in a single 90+ line method. Violates SRP and is hard to test
in isolation.

**Proposed fix**
- Extract cancellation logic to a `CancellationToken` class.
- Extract progress reporting to a dedicated callback handler.
- Extract metadata computation to a `_compute_video_metadata()` helper.
- Abstract `cv2` behind a `VideoReaderPort` to allow swapping backends.

---

### ISSUE-003 — `FrameStore` tightly coupled to Qt and mixes three concerns
| Field | Value |
|-------|-------|
| **Severity** | High |
| **Effort** | M |
| **Status** | open |
| **File(s)** | `app/track_app/frame_state/frame_store.py` |
| **Class(es)** | `FrameStore` |

**Description**
`FrameStore` inherits from `QObject` and uses `QPixmap` and Qt `Signal`s internally.
This couples the caching and preloading logic to the Qt framework, making it
impossible to test or reuse without a running Qt application.
Additionally, three concerns are mixed: cache management, preload scheduling
(with complex re-entrancy guards), and image I/O.

**Proposed fix**
- Extract a `FrameCacheService` that does not inherit from `QObject`. Use a
  `FrameLoadedListener` Protocol or plain callbacks.
- Extract preload scheduling into a `PreloadScheduler` using `queue.Queue` and
  `ThreadPoolExecutor`.
- Let a thin `FrameStoreQtAdapter` wrap `FrameCacheService` and emit Qt signals.

---

### ISSUE-004 — Method too long: `TrackDetectorService.detect_people_for_sequence()` (65+ lines)
| Field | Value |
|-------|-------|
| **Severity** | High |
| **Effort** | M |
| **Status** | open |
| **File(s)** | `app/track_app/sections/track_detector/service.py` |
| **Class(es)** | `TrackDetectorService` |

**Description**
`detect_people_for_sequence()` handles single-frame detection, batch detection, and
storage coordination in 65+ lines with nested conditionals. Mixes abstraction levels
and is hard to reason about or extend.

**Proposed fix**
- Extract `_detect_single_frame()` and `_detect_batch()` private methods.
- Abstract `DetectionsStore` behind a `DetectionsPersistencePort`.
- Share `_VALID_SUFFIXES` with `VideoManager` via a common constant (currently duplicated).

---

### ISSUE-005 — Duplicated pattern: bookmark update operations in `SequenceDataService`
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Effort** | S |
| **Status** | open |
| **File(s)** | `app/track_app/sections/video_manager/sequence_data_service.py` |
| **Class(es)** | `SequenceDataService` |

**Description**
`add_bookmark`, `move_bookmark`, `remove_bookmark`, `set_bookmark_name`, and
`set_bookmark_locked` all repeat the same file-read → domain-transform → file-write
pattern through `_update_bookmarks`. The code is not DRY and any change to the
update pattern must be replicated in all five methods.

**Proposed fix**
Introduce a generic `_apply_bookmark_transformation(updater_fn: Callable)` method
that encapsulates the read/transform/write cycle. Each public method passes only its
specific `bookmark_domain` function as the updater.

---

### ISSUE-006 — `MediaAdapter._resolve_input_path()` violates SRP and is hard to follow
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Effort** | M |
| **Status** | open |
| **File(s)** | `app/track_app/adapter.py` |
| **Class(es)** | `MediaAdapter` |

**Description**
Path resolution logic inside `MediaAdapter.load` handles `.dance_tracker.json` sidecars,
falls back to video files, and calls external resolvers — all mixed into a single method
on an adapter whose responsibility is bridging the UI↔app boundary, not parsing paths.

**Proposed fix**
Extract to a dedicated `InputPathResolver` class with a clear public interface and
thorough unit tests. `MediaAdapter.load` should delegate to it with a single call.

---

### ISSUE-007 — `Config` is a settings grab-bag with low cohesion
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Effort** | S |
| **Status** | open |
| **File(s)** | `app/track_app/config.py` |
| **Class(es)** | `Config` |

**Description**
`Config` mixes audio settings, detection API settings, and frame cache settings in a
single flat class (C: 6/10). Consumers that only need audio configuration are forced to
depend on the entire `Config` object.

**Proposed fix**
Group settings into nested pydantic models (`AudioConfig`, `DetectionConfig`,
`FrameConfig`) and compose them inside a root `Config`.

---

### ISSUE-008 — `MIN_BOOKMARK_DISTANCE_FRAMES` is hard-coded
| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Effort** | S |
| **Status** | open |
| **File(s)** | `app/track_app/sections/video_manager/bookmark_domain.py` |

**Description**
The minimum distance between bookmarks (25 frames) is a hard-coded module constant.
Users cannot configure it; extending requires a code change.

**Proposed fix**
Move to `Config` and pass as a parameter to the affected domain functions.

---

### ISSUE-009 — Magic number thresholds in detection adapters
| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Effort** | S |
| **Status** | open |
| **File(s)** | `app/track_app/sections/track_detector/detection_api_adapter.py`, `app/track_app/sections/track_detector/mpvision_adapter.py` |
| **Class(es)** | `DetectionApiPersonDetector`, `MPVisionPersonDetector` |

**Description**
Score thresholds (0.4) and `max_results` (2, 20) are constructor defaults with magic
numbers. Tuning requires code changes; values are not discoverable from config.

**Proposed fix**
Move defaults to `Config` / environment variables. Document their meaning with
constants (`MIN_DETECTION_SCORE = 0.4`).

---

### ISSUE-010 — Fragile binary image header parsing in `MockPersonDetector._image_size()`
| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Effort** | S |
| **Status** | open |
| **File(s)** | `app/track_app/sections/track_detector/mock_detectors.py` |
| **Class(es)** | `MockPersonDetector` |

**Description**
`_image_size()` manually parses PNG/BMP/JPEG binary headers to extract image dimensions.
This is brittle and will fail on non-standard or corrupted files. PIL/Pillow is already
a project dependency and handles this robustly.

**Proposed fix**
Replace binary parsing with `PIL.Image.open(path).size`.

---

### ISSUE-011 — Broad `except Exception` swallows errors silently
| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Effort** | S |
| **Status** | open |
| **File(s)** | `app/track_app/services/music_identifier/audio_extractor.py`, `app/track_app/sections/track_detector/detection_api_adapter.py` |

**Description**
Multiple locations catch `Exception` broadly without logging or error classification.
Failures are silently swallowed, making debugging difficult in production.

**Proposed fix**
Catch specific exception types (e.g. `subprocess.CalledProcessError`, `httpx.HTTPError`).
Add structured logging (`logging.getLogger(__name__).exception(...)`) at each catch site.

---

### ISSUE-012 — Duplicate `models.py` re-export in two locations
| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Effort** | XS |
| **Status** | open |
| **File(s)** | `app/track_app/sections/music_identifier/models.py`, `app/track_app/services/music_identifier/models.py` |

**Description**
Both files re-export the same types from `app.interface.music`. The duplication is
confusing; it is unclear which import path callers should use.

**Proposed fix**
Remove one copy. Decide on a canonical import path and update all callsites.

---

## Resolved Issues

*(None yet.)*
