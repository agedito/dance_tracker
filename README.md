# Proyecto Python para Dance Tracker

Este proyecto usa un entorno virtual (`virtualenv`) y requiere:

- `opencv-python`
- `numpy`
- `scipy`
- `matplotlib`
- `PyQt6`

## Estructura

- `logic.py`: lógica de procesamiento (detección demo / generación de frames).
- `ui.py`: interfaz PyQt (ventana y acciones de usuario).
- `main.py`: punto de entrada de la aplicación.

## Crear y activar entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Instalar dependencias

```bash
pip install -r requirements.txt
```

## Ejecutar interfaz

```bash
python main.py
```
