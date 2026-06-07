# YouTube to MP3 by Chapters

Aplicación de escritorio con interfaz gráfica (Tkinter) que descarga el audio de
un video de YouTube, lo convierte a MP3 a 320 kbps y lo parte en archivos
separados según los **capítulos nativos** del video. Cada MP3 queda
etiquetado con tags ID3 completos (título del track, número, artista, álbum,
año).

Pensada para podcasts largos, mixes de DJ, conferencias o álbumes subidos
como un único video con capítulos marcados en la descripción.

---

## Características

- Descarga audio de YouTube a 320 kbps CBR (MP3).
- Parte automáticamente en un MP3 por capítulo.
- Detecta y elimina el prefijo redundante del uploader en el título
  (`Artist - Artist - Album` → `Artist - Album`).
- Embebe tags ID3v2.4: `TIT2`, `TRCK`, `TPE1`, `TALB`, `TDRC`.
- Crea una carpeta por descarga: `<Artista> - <Álbum> (<Año>)`.
- GUI simple: input URL, picker de carpeta destino, botón comenzar, log
  con timestamp, progress bar, abrir carpeta al terminar.
- No re-codifica al partir: usa `ffmpeg -c copy` (cortes por frame MP3, sin
  pérdida y rápidos).

## Requisitos

- **Python 3.10+**
- **ffmpeg** (binario de sistema)
- **yt-dlp** y **mutagen** (pip)

### Instalación de dependencias de sistema

```bash
# Debian / Ubuntu
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Descargar de https://ffmpeg.org/download.html
```

### Instalación de dependencias Python

```bash
pip install -r requirements.txt
```

> **Nota sobre yt-dlp:** YouTube cambia sus mecanismos anti-bot seguido. Si
> la app empieza a fallar con errores `403 Forbidden` o `nsig extraction
> failed`, actualizá yt-dlp:
> ```bash
> pip install --user --break-system-packages --upgrade yt-dlp
> ```

## Uso

```bash
python3 youtube_to_mp3_by_chapters.py
```

1. Pegá la URL del video de YouTube.
2. Elegí la carpeta destino (default: `~/Música`).
3. Click en **Comenzar**.

Al terminar, la app crea una subcarpeta
`<Artista> - <Álbum> (<Año>)` con un MP3 por capítulo, ya etiquetado.

### Restricciones

- El video **debe tener capítulos nativos** (timestamps en la descripción o
  marcadores del player). Si no los tiene, la app muestra un mensaje claro
  y no descarga nada.
- La calidad es fija a 320 kbps. No hay opción de cambiarla desde la GUI.

## Estructura del proyecto

```
youtube-to-mp3-by-chapters/
├── youtube_to_mp3_by_chapters.py   # Entry point
├── gui.py                          # Tkinter: ventana, threading, log
├── downloader.py                   # Wrapper de yt-dlp + split con ffmpeg
├── metadata.py                     # Tagging ID3 con mutagen
├── utils.py                        # Sanitización de nombres, derivar carpeta
├── requirements.txt                # Dependencias pip
├── CHANGELOG.md                    # Historial de versiones
├── README.md                       # Este archivo
└── .gitignore
```

### Flujo interno

1. `gui.py` lanza un thread que llama a `downloader.fetch_metadata(url)` —
   `yt-dlp --dump-single-json` para leer la metadata.
2. `downloader.validate_chapters(meta)` exige ≥ 2 capítulos; si no, aborta.
3. `utils.derive_album_dir(...)` arma el nombre de carpeta, eliminando el
   prefijo redundante del artista y capeando a 120 chars.
4. `downloader.download_chapters(...)` descarga el audio completo con
   `yt-dlp` y luego divide con `ffmpeg -c copy` por timestamp.
5. Para cada MP3 resultante, `metadata.tag_mp3(...)` escribe los tags ID3.
6. El log de la GUI muestra cada paso con timestamp. El botón **Abrir
   carpeta** se habilita al terminar.

## Solución de problemas

### `Error: yt-dlp falló al descargar` con `HTTP 403` o `nsig extraction failed`

Versión vieja de yt-dlp. Actualizá:
```bash
pip install --user --break-system-packages --upgrade yt-dlp
```

### `[Errno 36] File name too long`

El título del video es demasiado largo. La app lo capea a 120 chars en el
nombre de la carpeta, pero si la ruta completa (incluyendo la carpeta
destino) supera 255 bytes, fallará. Probá con una carpeta destino con
nombres más cortos.

### `Este video no tiene capítulos`

La app solo funciona con videos que tengan capítulos nativos. Si el video
no los tiene, no hay forma de partirlo automáticamente sin detección de
silencios (que está fuera de scope).

### La GUI no abre / `couldn't connect to display`

La GUI requiere un display X11/Wayland. En servidores headless no funciona
(la lógica sí — los módulos son testeables de forma independiente).

## Licencia

MIT (o la que elijas — ajustá según necesidad).
