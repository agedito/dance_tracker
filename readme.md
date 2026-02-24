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
- PySide6 6.10.2 (ui)
- pydantic-settings 2.13.1 (to use configs from .env files)

## Frame folders and cache

- Drag and drop a local folder with images (`png`, `jpg`, `jpeg`, `bmp`, `webp`) over the main viewer to load frames.
- The app preloads frames around the current one using `FRAME_CACHE_RADIUS` from `config.env` (default: `25`).
