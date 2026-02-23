# Dance Tracker

A dance tracker app
```bash
make run
```

## Environment

### Create virtual environment
```bash
python -m venv .venv
```

### Install dependencies
```bash
make dependencies
```

### Libraries
- numpy 2.4.2
- scipy 1.17.1
- opencv-python 4.13.0.92
- PySide6 6.10.2
## Frame folders and cache

- Drag and drop a local folder with images (`png`, `jpg`, `jpeg`, `bmp`, `webp`) over the main viewer to load frames.
- The app preloads frames around the current one using `FRAME_CACHE_RADIUS` from `config.env` (default: `25`).


## CUDA mode

- Configure `ENABLE_CUDA=true` in `config.env` to request CUDA mode.
- If CUDA is active (flag enabled and supported by OpenCV + GPU), timeline drag/scrub uses full-resolution frames.
- If CUDA is disabled or unavailable, timeline drag/scrub uses `frames_mino` proxy images when available for smoother interaction.
