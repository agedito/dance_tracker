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
## Carga de frames

- Arrastra una carpeta con imágenes (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.webp`) sobre el viewer principal para usarla como fuente de frames.
- El viewer hace precarga/caché de frames por delante y por detrás del frame actual para que la navegación sea más fluida.
- El tamaño de caché se configura en `config.json` con `frame_cache_radius` (por defecto `25`, equivalente a ±25 frames).
