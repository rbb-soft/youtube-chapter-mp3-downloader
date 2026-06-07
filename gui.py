import os
import platform
import queue
import subprocess
import threading
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from downloader import (
    DownloadError,
    build_album_dir_name,
    download_chapters,
    fetch_metadata,
    validate_chapters,
)
from metadata import tag_mp3
from utils import sanitize_filename


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("YouTube to MP3 by Chapters")
        self.geometry("720x600")
        self.minsize(600, 500)

        self.log_queue: queue.Queue = queue.Queue()
        self.last_album_path: Path | None = None
        self.open_after_var = tk.BooleanVar(value=True)

        self._build_ui()
        self.after(100, self._poll_queue)
        self._set_status("Listo")

    def _build_ui(self) -> None:
        main = ttk.Frame(self, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="URL de YouTube:").pack(anchor=tk.W)
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(main, textvariable=self.url_var)
        url_entry.pack(fill=tk.X, pady=(2, 10))
        url_entry.focus()

        ttk.Label(main, text="Carpeta destino:").pack(anchor=tk.W)
        folder_frame = ttk.Frame(main)
        folder_frame.pack(fill=tk.X, pady=(2, 10))
        self.folder_var = tk.StringVar(value=str(Path.home() / "Música"))
        ttk.Entry(folder_frame, textvariable=self.folder_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(folder_frame, text="Elegir...", command=self._pick_folder).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        self.start_btn = ttk.Button(btn_frame, text="Comenzar", command=self._on_start)
        self.start_btn.pack(side=tk.LEFT)
        self.open_btn = ttk.Button(
            btn_frame,
            text="Abrir carpeta",
            command=self._on_open,
            state=tk.DISABLED,
        )
        self.open_btn.pack(side=tk.LEFT, padx=(10, 0))
        ttk.Checkbutton(
            btn_frame, text="Abrir al terminar", variable=self.open_after_var
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.status_var = tk.StringVar(value="Listo")
        ttk.Label(main, textvariable=self.status_var).pack(anchor=tk.W)
        self.progress = ttk.Progressbar(main, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(2, 10))

        ttk.Label(main, text="Log:").pack(anchor=tk.W)
        self.log_text = scrolledtext.ScrolledText(
            main, height=18, state=tk.DISABLED, font=("Monospace", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _pick_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)

    def _log(self, msg: str) -> None:
        self.log_queue.put(("log", msg))

    def _set_status(self, msg: str) -> None:
        self.log_queue.put(("status", msg))

    def _set_progress(self, running: bool) -> None:
        self.log_queue.put(("progress", running))

    def _on_start(self) -> None:
        url = self.url_var.get().strip()
        folder = self.folder_var.get().strip()
        if not url:
            messagebox.showwarning("Falta URL", "Ingresá una URL de YouTube.")
            return
        if not folder:
            folder = str(Path.home())
            self.folder_var.set(folder)

        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)
        self.open_btn.configure(state=tk.DISABLED)
        self.start_btn.configure(state=tk.DISABLED)
        self.last_album_path = None

        threading.Thread(
            target=self._run_download,
            args=(url, Path(folder)),
            daemon=True,
        ).start()

    def _run_download(self, url: str, dest_dir: Path) -> None:
        try:
            meta = fetch_metadata(url, self._log)
            chapters = validate_chapters(meta)
            self._log(f"Encontrados {len(chapters)} capítulos")

            album_dir_name = build_album_dir_name(meta)
            self._log(f"Álbum destino: {album_dir_name}")

            album = sanitize_filename(meta.get("title") or "")
            artist = sanitize_filename(
                meta.get("uploader") or meta.get("channel") or ""
            )
            upload_date = meta.get("upload_date") or ""
            year = upload_date[:4] if len(upload_date) >= 4 else ""

            self._set_progress(True)
            mp3s = download_chapters(url, dest_dir, album_dir_name, chapters, self._log)
            self._set_progress(False)

            self._log(f"Etiquetando {len(mp3s)} MP3s...")
            for i, (mp3_path, chapter) in enumerate(zip(mp3s, chapters), start=1):
                title = sanitize_filename(chapter.get("title") or f"Track {i}")
                tag_mp3(mp3_path, track_number=i, title=title, artist=artist, album=album, year=year)
                self._log(f"  {i}/{len(mp3s)} {title}")

            album_path = dest_dir / album_dir_name
            self.last_album_path = album_path
            self._set_status(f"✓ {len(mp3s)} tracks en {album_path}")
            self._log(f"✓ Listo: {len(mp3s)} tracks en {album_path}")
            self.log_queue.put(("done", str(album_path)))
        except DownloadError as e:
            self._set_progress(False)
            self._set_status("Error")
            self._log(f"✗ Error: {e}")
            messagebox.showerror("Error de descarga", str(e))
        except Exception as e:
            self._set_progress(False)
            self._set_status("Error inesperado")
            self._log(f"✗ Error inesperado: {e}")
            messagebox.showerror("Error inesperado", str(e))
        finally:
            self.log_queue.put(("enable_start", None))

    def _on_open(self) -> None:
        if self.last_album_path and self.last_album_path.exists():
            self._open_in_file_manager(self.last_album_path)

    def _open_in_file_manager(self, path: Path) -> None:
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif system == "Darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta: {e}")

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, value = self.log_queue.get_nowait()
                if kind == "log":
                    self._append_log(value)
                elif kind == "status":
                    self.status_var.set(value)
                elif kind == "progress":
                    if value:
                        self.progress.start(10)
                    else:
                        self.progress.stop()
                elif kind == "done":
                    self.open_btn.configure(state=tk.NORMAL)
                    if self.open_after_var.get() and self.last_album_path:
                        self._open_in_file_manager(self.last_album_path)
                elif kind == "enable_start":
                    self.start_btn.configure(state=tk.NORMAL)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _append_log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{ts}  {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
