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
- imageio-ffmpeg 0.6.0 (bundled ffmpeg binary for audio extraction)

## Frame folders and cache

- Drag and drop a local folder with images (`png`, `jpg`, `jpeg`, `bmp`, `webp`) over the main viewer to load frames.
- The app preloads frames around the current one using `FRAME_CACHE_RADIUS` from `config.env` (default: `25`).

## Music identification

- When dropping a local video, the app extracts short audio snippets at configurable points using ffmpeg (bundled via `imageio-ffmpeg`, no global installation required) and tries to identify the song using `audd.io`.
- Configure `AUDIO_SAMPLE_SECONDS` and `AUDIO_SAMPLE_POINTS` in `preferences/app.env` to control snippet length and how many equidistant points are used (always including the beginning and the end of the video).
- Configure `AUDD_API_TOKEN` and any other sensitive variables in `secrets.env` at the repository root.
- Song metadata is displayed in the **Music** tab.
