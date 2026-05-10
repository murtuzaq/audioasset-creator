import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "utility", "error_log_py"))

import error_log
from audioasset_creator import save
from app_lyrics_editor import LyricsEditor

error_log.setup(os.path.join(_HERE, "audioasset_creator.err"))

AUDIO_FILETYPES = [
    ("Audio files", "*.mp3 *.wav *.flac *.aac *.ogg *.m4a *.wma"),
    ("All files", "*.*"),
]
TRANSCRIPT_FILETYPES = [
    ("Text files", "*.txt"),
    ("All files", "*.*"),
]
DEFAULT_INCREMENT = 5.0


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Audio Asset Creator")
        self.resizable(False, False)
        self._file_path = tk.StringVar()
        self._transcribe = tk.BooleanVar()
        self._increment = tk.StringVar(value=str(DEFAULT_INCREMENT))
        self._reference_path = tk.StringVar()
        self._status = tk.StringVar()
        self._last_info_path: str | None = None
        self._build_ui()
        self._transcribe.trace_add("write", self._on_transcribe_toggle)
        error_log.install_hook(lambda: self)

    def _build_ui(self):
        file_frame = tk.Frame(self, padx=16, pady=16)
        file_frame.pack(fill="x")

        tk.Label(file_frame, text="Audio File:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        tk.Entry(file_frame, textvariable=self._file_path, width=48, state="readonly").grid(row=0, column=1)
        tk.Button(file_frame, text="Browse", command=self._browse_audio).grid(row=0, column=2, padx=(8, 0))

        tk.Checkbutton(
            self,
            text="Transcribe lyrics",
            variable=self._transcribe,
        ).pack(anchor="w", padx=16)

        self._tx_frame = tk.Frame(self, padx=32)
        self._tx_frame.pack(anchor="w", fill="x", pady=(2, 8))

        tk.Label(self._tx_frame, text="Lyric increment (s):").grid(row=0, column=0, sticky="w")
        self._increment_entry = tk.Entry(self._tx_frame, textvariable=self._increment, width=6)
        self._increment_entry.grid(row=0, column=1, sticky="w", padx=(6, 0))

        tk.Label(self._tx_frame, text="Reference transcript (optional):").grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )
        self._reference_entry = tk.Entry(
            self._tx_frame, textvariable=self._reference_path, width=38, state="readonly"
        )
        self._reference_entry.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(6, 0))
        self._reference_browse_btn = tk.Button(
            self._tx_frame, text="Browse", command=self._browse_reference
        )
        self._reference_browse_btn.grid(row=1, column=2, padx=(6, 0), pady=(6, 0))
        self._reference_clear_btn = tk.Button(
            self._tx_frame, text="Clear", command=lambda: self._reference_path.set("")
        )
        self._reference_clear_btn.grid(row=1, column=3, padx=(4, 0), pady=(6, 0))

        self._tx_widgets = [
            self._increment_entry,
            self._reference_browse_btn,
            self._reference_clear_btn,
        ]
        self._set_tx_state("disabled")

        btn_row = tk.Frame(self)
        btn_row.pack(pady=(0, 6))

        self._generate_btn = tk.Button(btn_row, text="Generate", command=self._generate, padx=20, pady=6)
        self._generate_btn.pack(side="left", padx=(0, 8))

        self._edit_btn = tk.Button(
            btn_row, text="Edit Lyrics", command=self._open_editor, padx=20, pady=6, state="disabled"
        )
        self._edit_btn.pack(side="left")

        self._progress_frame = tk.Frame(self, height=20)
        self._progress_frame.pack(fill="x", padx=16, pady=(0, 4))
        self._progress_frame.pack_propagate(False)

        self._progress = ttk.Progressbar(self._progress_frame, mode="determinate", maximum=100)

        tk.Label(self, textvariable=self._status, fg="gray").pack(pady=(0, 12))

    def _set_tx_state(self, state: str):
        for w in self._tx_widgets:
            w.config(state=state)

    def _on_transcribe_toggle(self, *_):
        self._set_tx_state("normal" if self._transcribe.get() else "disabled")
        if not self._transcribe.get():
            self._edit_btn.config(state="disabled")

    def _browse_audio(self):
        path = filedialog.askopenfilename(filetypes=AUDIO_FILETYPES)
        if path:
            self._file_path.set(path)
            self._edit_btn.config(state="disabled")
            self._last_info_path = None

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
        self._edit_btn.config(state="disabled")
        self._set_busy(True)
        threading.Thread(target=self._run_generate, args=(path,), daemon=True).start()

    def _run_generate(self, path: str):
        transcribing = self._transcribe.get()

        def on_progress(fraction):
            self.after(0, lambda: self._update_progress(int(fraction * 100)))

        try:
            out = save(
                path,
                transcribe=transcribing,
                transcribe_increment=self._increment_value(),
                progress_callback=on_progress if transcribing else None,
            )
            self.after(0, lambda: self._on_done(out, transcribing))
        except Exception as e:
            self.after(0, lambda: self._on_error(e))

    def _update_progress(self, value: int):
        self._progress["value"] = value

    def _on_done(self, out: str, has_lyrics: bool):
        self._update_progress(100)
        self._set_busy(False)
        if has_lyrics:
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
        if not self._last_info_path:
            return
        LyricsEditor(self, self._last_info_path, reference_transcript=self._reference_text())


if __name__ == "__main__":
    App().mainloop()
