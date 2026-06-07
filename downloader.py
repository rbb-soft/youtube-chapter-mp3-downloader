import json
import subprocess
from pathlib import Path
from typing import Callable

from utils import sanitize_filename, derive_album_dir

Callback = Callable[[str], None]


class DownloadError(Exception):
    pass


def fetch_metadata(url: str, log: Callback) -> dict:
    """Fetch video metadata as a dict using `yt-dlp --dump-single-json`."""
    log("Validando URL y leyendo metadata del video...")
    result = subprocess.run(
        ["yt-dlp", "--dump-single-json", "--no-warnings", "--no-playlist", url],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DownloadError(
            f"No se pudo leer la metadata. ¿URL válida?\n\n{result.stderr.strip()}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise DownloadError(f"Respuesta inválida de yt-dlp: {e}") from e


def validate_chapters(meta: dict) -> list[dict]:
    chapters = meta.get("chapters") or []
    if len(chapters) < 2:
        raise DownloadError(
            "Este video no tiene capítulos. Esta app solo funciona con "
            "videos que tengan capítulos nativos (timestamps en la descripción "
            "o marcadores del reproductor)."
        )
    return chapters


def build_album_dir_name(meta: dict) -> str:
    artist = meta.get("uploader") or meta.get("channel") or "Unknown Artist"
    album = meta.get("title") or "Unknown Title"
    upload_date = meta.get("upload_date") or ""
    year = upload_date[:4] if len(upload_date) >= 4 else ""
    return derive_album_dir(artist, album, year)


def _download_full_audio(
    url: str, album_path: Path, log: Callback
) -> Path:
    """Download the full audio as a single MP3, return its path."""
    log("Descargando audio completo...")
    template = str(album_path / "full.%(ext)s")
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--postprocessor-args", "ffmpeg:-b:a 320k",
        "--no-embed-metadata",
        "--no-embed-chapters",
        "--no-playlist",
        "-o", template,
        url,
    ]
    result = subprocess.run(
        cmd,
        cwd=album_path.parent,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DownloadError(
            f"yt-dlp falló al descargar:\n\n{result.stderr.strip() or result.stdout.strip()}"
        )

    downloaded = list(album_path.glob("full.*"))
    if not downloaded:
        raise DownloadError(
            "yt-dlp terminó sin errores pero no se generó el archivo de audio."
        )
    return downloaded[0]


def _split_by_chapters(
    full_audio: Path,
    chapters: list[dict],
    album_path: Path,
    log: Callback,
) -> list[Path]:
    """Split the full audio into per-chapter MP3s using ffmpeg -c copy."""
    log(f"Dividiendo en {len(chapters)} capítulos con ffmpeg...")
    total = len(chapters)
    outputs: list[Path] = []

    for i, chapter in enumerate(chapters, start=1):
        title = sanitize_filename(chapter.get("title") or f"Track {i}")
        output = album_path / f"{i:02d} - {title}.mp3"
        start = float(chapter.get("start_time") or 0)
        end = chapter.get("end_time")

        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(full_audio),
            "-ss", f"{start:.3f}",
        ]
        if end is not None:
            cmd.extend(["-to", f"{float(end):.3f}"])
        cmd.extend(["-c", "copy", str(output)])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not output.exists() or output.stat().st_size == 0:
            raise DownloadError(
                f"ffmpeg falló al cortar el capítulo {i} ({title!r}):\n"
                f"{result.stderr.strip() or 'archivo vacío'}"
            )
        outputs.append(output)
        log(f"  {i}/{total} {title}")

    return outputs


def download_chapters(
    url: str,
    dest_dir: Path,
    album_dir_name: str,
    chapters: list[dict],
    log: Callback,
) -> list[Path]:
    """Download the audio, split by chapters, return list of MP3 paths.

    Strategy: download the full audio as one MP3, then split with ffmpeg
    using -c copy (no re-encoding, frame-aligned cuts). This gives full
    control over filenames and avoids yt-dlp's split-chapter naming quirks.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    album_path = dest_dir / album_dir_name
    album_path.mkdir(parents=True, exist_ok=True)

    try:
        full_audio = _download_full_audio(url, album_path, log)
        mp3s = _split_by_chapters(full_audio, chapters, album_path, log)
    finally:
        for leftover in album_path.glob("full.*"):
            try:
                leftover.unlink()
            except OSError:
                pass

    return mp3s
