# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.1.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [2.0.0] - 2026-06-07

### Added
- Interfaz gráfica con Tkinter (input URL, picker de carpeta destino, botón
  comenzar, log con timestamp, progress bar).
- Descarga de audio de YouTube a 320 kbps CBR (MP3).
- Partición automática del audio en un MP3 por capítulo nativo del video.
- Embedding de tags ID3v2.4 (`TIT2`, `TRCK`, `TPE1`, `TALB`, `TDRC`) en cada
  MP3 resultante.
- Detección y eliminación del prefijo redundante del uploader en el título
  (ej: `Patricio Rey y sus Redonditos de Ricota - Patricio Rey y sus
  Redonditos de Ricota - Un Baion...` → `Patricio Rey y sus Redonditos de
  Ricota - Un Baion...`).
- Capa el nombre de la carpeta destino a 120 caracteres para evitar
  `ENAMETOOLONG` del filesystem.
- Threading en la GUI: la descarga corre en background y no congela la UI.
- Apertura de la carpeta destino al terminar (opcional, via checkbox).

### Decisiones técnicas
- Split con `ffmpeg -c copy` en lugar de `yt-dlp --split-chapters`, porque
  el segundo ignora el `-o` template y usa su propio patrón de nombres largo
  e inmanejable.
- Sin re-encoding en el split: cortes por frame MP3 (rápido, sin pérdida).
  Trade-off: puede haber ~26ms de silenciito al borde de cada track.

### Fuera de scope
- Detección automática de capítulos por silencios.
- Timestamps manuales.
- Otros formatos de audio (FLAC, AAC, OGG).
- Selección de calidad desde la GUI.
- Persistencia de historial o configuración.
