import json
import os
import re
import sys
import tempfile
import threading
import tkinter as tk
import urllib.parse
import urllib.request
import webbrowser
from tkinter import filedialog, ttk

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "utility", "error_log_py"))
sys.path.insert(0, os.path.join(_HERE, "utility", "git_version_py"))

import error_log
import git_version
from audioasset_creator import save
from app_lyrics_editor import LyricsEditor

error_log.setup(os.path.join(_HERE, "audioasset_creator.err"))
_VERSION = git_version.get(_HERE)

AUDIO_FILETYPES = [
    ("Audio files", "*.mp3 *.wav *.flac *.aac *.ogg *.m4a *.wma"),
    ("All files", "*.*"),
]
TRANSCRIPT_FILETYPES = [
    ("Text files", "*.txt"),
    ("All files", "*.*"),
]
DEFAULT_INCREMENT = 5.0

_YT_RE = re.compile(r"(youtube\.com|youtu\.be)", re.IGNORECASE)
_CONVERTERS = [
    ("cobalt.tools", "https://cobalt.tools/"),
    ("y2mate", "https://www.y2mate.com/"),
    ("yt1s", "https://yt1s.com/"),
    ("ytmp3.cc", "https://ytmp3.cc/"),
]


class App(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title(f"Audio Asset Creator {_VERSION}")
        self.resizable(False, False)
        self._file_path = tk.StringVar()
        self._save_dir = tk.StringVar()
        self._transcribe = tk.BooleanVar()
        self._increment = tk.StringVar(value=str(DEFAULT_INCREMENT))
        self._reference_path = tk.StringVar()
        self._status = tk.StringVar()
        self._last_info_path: str | None = None
        self._build_ui()
        error_log.install_hook(lambda: self)

    def _build_ui(self):
        # Audio file row
        file_frame = tk.Frame(self, padx=16)
        file_frame.pack(fill="x", pady=(16, 4))

        tk.Label(file_frame, text="Audio File:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        tk.Entry(file_frame, textvariable=self._file_path, width=48, state="readonly").grid(row=0, column=1)
        tk.Button(file_frame, text="Browse", command=self._browse_audio).grid(row=0, column=2, padx=(8, 0))
        tk.Button(file_frame, text="From URL…", command=self._from_url).grid(row=0, column=3, padx=(4, 0))

        # Save directory row
        tk.Label(file_frame, text="Save to:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(6, 0))
        tk.Entry(file_frame, textvariable=self._save_dir, width=48, state="readonly").grid(row=1, column=1, pady=(6, 0))
        tk.Button(file_frame, text="Browse", command=self._browse_save_dir).grid(row=1, column=2, padx=(8, 0), pady=(6, 0))

        # Separator
        tk.Frame(self, height=1, bg="#cccccc").pack(fill="x", padx=16, pady=(8, 4))

        # Transcribe checkbox
        tk.Checkbutton(self, text="Transcribe lyrics", variable=self._transcribe).pack(anchor="w", padx=16)

        # Lyrics options — always visible
        opts_frame = tk.Frame(self, padx=16)
        opts_frame.pack(anchor="w", fill="x", pady=(4, 8))

        tk.Label(opts_frame, text="Lyric increment (s):").grid(row=0, column=0, sticky="w")
        tk.Entry(opts_frame, textvariable=self._increment, width=6).grid(
            row=0, column=1, sticky="w", padx=(6, 0)
        )

        tk.Label(opts_frame, text="Reference transcript (optional):").grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )
        tk.Entry(opts_frame, textvariable=self._reference_path, width=38, state="readonly").grid(
            row=1, column=1, sticky="w", padx=(6, 0), pady=(6, 0)
        )
        tk.Button(opts_frame, text="Browse", command=self._browse_reference).grid(
            row=1, column=2, padx=(6, 0), pady=(6, 0)
        )
        tk.Button(opts_frame, text="Clear", command=lambda: self._reference_path.set("")).grid(
            row=1, column=3, padx=(4, 0), pady=(6, 0)
        )

        # Action buttons
        btn_row = tk.Frame(self)
        btn_row.pack(pady=(0, 6))

        self._generate_btn = tk.Button(btn_row, text="Generate", command=self._generate, padx=20, pady=6)
        self._generate_btn.pack(side="left", padx=(0, 8))

        self._edit_btn = tk.Button(
            btn_row, text="Edit Lyrics", command=self._open_editor, padx=20, pady=6, state="disabled"
        )
        self._edit_btn.pack(side="left")

        # Progress + status
        self._progress_frame = tk.Frame(self, height=20)
        self._progress_frame.pack(fill="x", padx=16, pady=(0, 4))
        self._progress_frame.pack_propagate(False)
        self._progress = ttk.Progressbar(self._progress_frame, mode="determinate", maximum=100)

        tk.Label(self, textvariable=self._status, fg="gray").pack(pady=(0, 12))

    def _browse_audio(self):
        path = filedialog.askopenfilename(filetypes=AUDIO_FILETYPES)
        if not path:
            return
        self._file_path.set(path)
        audio_dir = os.path.dirname(os.path.abspath(path))
        self._save_dir.set(audio_dir)
        self._refresh_edit_btn(audio_dir, os.path.basename(path))

    def _from_url(self):
        dialog = _UrlImportDialog(self)
        self.wait_window(dialog)
        if dialog.result_path:
            path = dialog.result_path
            self._file_path.set(path)
            audio_dir = os.path.dirname(os.path.abspath(path))
            self._save_dir.set(audio_dir)
            self._refresh_edit_btn(audio_dir, os.path.basename(path))

    def _browse_save_dir(self):
        path = filedialog.askdirectory()
        if path:
            self._save_dir.set(path)
            audio = self._file_path.get()
            if audio:
                self._refresh_edit_btn(path, os.path.basename(audio))

    def _refresh_edit_btn(self, save_dir: str, audio_basename: str):
        base = os.path.splitext(audio_basename)[0]
        info_path = os.path.join(save_dir, base + ".info")
        self._last_info_path = info_path if os.path.exists(info_path) else None
        self._edit_btn.config(state="normal")

    def _browse_reference(self):
        path = filedialog.askopenfilename(filetypes=TRANSCRIPT_FILETYPES)
        if path:
            self._reference_path.set(path)

    def _increment_value(self) -> float:
        try:
            v = float(self._increment.get())
            return v if v > 0 else DEFAULT_INCREMENT
        except ValueError:
            return DEFAULT_INCREMENT

    def _reference_text(self) -> str | None:
        path = self._reference_path.get()
        if not path:
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _generate(self):
        path = self._file_path.get()
        if not path:
            from tkinter import messagebox
            messagebox.showwarning("No file selected", "Please select an audio file first.")
            return
        self._set_busy(True)
        threading.Thread(target=self._run_generate, args=(path,), daemon=True).start()

    def _run_generate(self, path: str):
        transcribing = self._transcribe.get()
        out_dir = self._save_dir.get() or None

        def on_progress(fraction):
            self.after(0, lambda: self._update_progress(int(fraction * 100)))

        try:
            out = save(
                path,
                transcribe=transcribing,
                transcribe_increment=self._increment_value(),
                output_dir=out_dir,
                progress_callback=on_progress if transcribing else None,
            )
            self.after(0, lambda: self._on_done(out))
        except Exception as e:
            self.after(0, lambda e=e: self._on_error(e))

    def _update_progress(self, value: int):
        self._progress["value"] = value

    def _on_done(self, out: str):
        self._update_progress(100)
        self._set_busy(False)
        self._last_info_path = out
        self._edit_btn.config(state="normal")
        from tkinter import messagebox
        messagebox.showinfo("Done", f"Asset saved to:\n{out}")

    def _on_error(self, exc: Exception):
        self._set_busy(False)
        error_log.show(self, exc, context="generate")

    def _set_busy(self, busy: bool):
        if busy:
            self._progress["value"] = 0
            self._progress.pack(fill="x", expand=True)
            self._generate_btn.config(state="disabled")
            self._status.set(
                "Transcribing lyrics, this may take a moment..." if self._transcribe.get() else "Generating..."
            )
        else:
            self._progress.pack_forget()
            self._progress["value"] = 0
            self._generate_btn.config(state="normal")
            self._status.set("")

    def _open_editor(self):
        audio_path = self._file_path.get()
        if not audio_path:
            return
        if self._last_info_path:
            info_path = self._last_info_path
        else:
            save_dir = self._save_dir.get() or os.path.dirname(os.path.abspath(audio_path))
            base = os.path.splitext(os.path.basename(audio_path))[0]
            info_path = os.path.join(save_dir, base + ".info")
        LyricsEditor(
            self,
            info_path=info_path,
            audio_path=audio_path,
            increment=self._increment_value(),
            reference_transcript=self._reference_text(),
        )


_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".webm", ".opus"}


def _download_audio(
    url: str,
    username: str = "",
    password: str = "",
    progress_callback=None,  # (fraction: float, status_text: str) -> None
) -> str:
    dest_dir = tempfile.mkdtemp(prefix="audioasset_")

    # Try yt-dlp (handles YouTube, SoundCloud, Bandcamp, etc.)
    try:
        import yt_dlp

        def _yt_hook(d):
            if progress_callback is None:
                return
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                fraction = downloaded / total if total else 0
                parts = []
                if total:
                    parts.append(f"{downloaded / 1e6:.1f} / {total / 1e6:.1f} MB")
                speed = d.get("speed")
                if speed:
                    parts.append(f"{speed / 1e6:.1f} MB/s")
                eta = d.get("eta")
                if eta:
                    parts.append(f"{eta}s left")
                progress_callback(fraction, " • ".join(parts))
            elif d["status"] == "finished":
                progress_callback(1.0, "Processing…")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(dest_dir, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [_yt_hook],
        }
        if username:
            ydl_opts["username"] = username
            ydl_opts["password"] = password

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        for fname in os.listdir(dest_dir):
            if os.path.splitext(fname)[1].lower() in _AUDIO_EXTENSIONS:
                return os.path.join(dest_dir, fname)
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: direct HTTP download with chunked progress
    if progress_callback:
        progress_callback(0.0, "Trying direct download…")
    parsed = urllib.parse.urlparse(url)
    filename = os.path.basename(parsed.path) or "audio"
    if not os.path.splitext(filename)[1]:
        filename += ".mp3"
    dest_path = os.path.join(dest_dir, filename)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    fraction = downloaded / total if total else 0
                    text = f"{downloaded / 1e6:.1f} MB"
                    if total:
                        text += f" / {total / 1e6:.1f} MB"
                    progress_callback(fraction, text)
    return dest_path


class _UrlImportDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Import from URL")
        self.resizable(False, False)
        self.result_path: str | None = None
        self._url = tk.StringVar()
        self._show_login = tk.BooleanVar()
        self._username = tk.StringVar()
        self._password = tk.StringVar()
        self._status = tk.StringVar()
        self._build_ui()
        self.grab_set()
        self.transient(parent)

    def _build_ui(self):
        # URL row
        url_frame = tk.Frame(self, padx=16)
        url_frame.pack(fill="x", pady=(12, 0))
        tk.Label(url_frame, text="URL:").pack(side="left", padx=(0, 8))
        url_entry = tk.Entry(url_frame, textvariable=self._url, width=54)
        url_entry.pack(side="left", fill="x", expand=True)
        url_entry.focus_set()
        url_entry.bind("<KeyRelease>", lambda _e: self._on_url_change())
        url_entry.bind("<FocusOut>", lambda _e: self._on_url_change())

        # Converter shortcuts (shown only when a YouTube URL is detected)
        self._converter_frame = tk.Frame(self, padx=16)
        tk.Label(self._converter_frame, text="Open in converter:", fg="gray").pack(side="left", padx=(0, 8))
        for name, site_url in _CONVERTERS:
            tk.Button(
                self._converter_frame, text=name, padx=6, pady=2,
                command=lambda u=site_url: self._open_converter(u),
            ).pack(side="left", padx=(0, 4))

        # Login toggle
        self._login_check = tk.Checkbutton(
            self, text="Login required (optional)",
            variable=self._show_login, command=self._toggle_login,
        )
        self._login_check.pack(anchor="w", padx=16, pady=(8, 0))

        # Login fields (hidden until toggled on)
        self._login_frame = tk.Frame(self, padx=16)
        lf = self._login_frame
        tk.Label(lf, text="Username:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        tk.Entry(lf, textvariable=self._username, width=36).grid(row=0, column=1, sticky="ew")
        tk.Label(lf, text="Password:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
        tk.Entry(lf, textvariable=self._password, width=36, show="*").grid(row=1, column=1, pady=(4, 0))

        # Import button
        self._import_btn = tk.Button(self, text="Import", command=self._start_import, padx=16)
        self._import_btn.pack(pady=(10, 6))

        # Progress bar (hidden until download starts)
        self._progress = ttk.Progressbar(self, mode="determinate", maximum=100, length=390)

        # Status label
        self._status_label = tk.Label(self, textvariable=self._status, fg="gray", wraplength=390)
        self._status_label.pack(pady=(0, 12))

        self.bind("<Return>", lambda _e: self._start_import())

    def _on_url_change(self):
        url = self._url.get().strip()
        if _YT_RE.search(url):
            if not self._converter_frame.winfo_ismapped():
                self._converter_frame.pack(fill="x", pady=(6, 0), before=self._login_check)
        else:
            self._converter_frame.pack_forget()

    def _open_converter(self, site_url: str):
        yt_url = self._url.get().strip()
        self.clipboard_clear()
        self.clipboard_append(yt_url)
        webbrowser.open(site_url)
        self._status.set("YouTube URL copied to clipboard — paste it on the converter site")

    def _toggle_login(self):
        if self._show_login.get():
            self._login_frame.pack(fill="x", pady=(4, 0), before=self._import_btn)
        else:
            self._login_frame.pack_forget()

    def _start_import(self):
        url = self._url.get().strip()
        if not url:
            return
        self._import_btn.config(state="disabled")
        self._status.set("Connecting…")
        self._progress["value"] = 0
        self._progress.pack(padx=16, pady=(0, 4), before=self._status_label)
        username = self._username.get().strip() if self._show_login.get() else ""
        password = self._password.get() if self._show_login.get() else ""
        threading.Thread(target=self._run, args=(url, username, password), daemon=True).start()

    def _run(self, url: str, username: str, password: str):
        def on_progress(fraction, text):
            pct = int(fraction * 100)
            self.after(0, lambda p=pct, t=text: self._update_progress(p, t))

        try:
            path = _download_audio(url, username=username, password=password, progress_callback=on_progress)
            self.after(0, lambda: self._on_done(path))
        except Exception as exc:
            self.after(0, lambda e=exc: self._on_error(e))

    def _update_progress(self, pct: int, text: str):
        self._progress["value"] = pct
        self._status.set(text)

    def _on_done(self, path: str):
        self.result_path = path
        self.destroy()

    def _on_error(self, exc: Exception):
        self._import_btn.config(state="normal")
        self._progress.pack_forget()
        self._status.set(f"Error: {exc}")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    app = App(root)
    app.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()
