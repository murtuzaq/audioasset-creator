import os
import threading
import tkinter as tk
from tkinter import filedialog, ttk

import apputils
from audioasset_creator import save

_HERE = os.path.dirname(os.path.abspath(__file__))
apputils.setup(os.path.join(_HERE, "audioasset_creator.err"))

AUDIO_FILETYPES = [
    ("Audio files", "*.mp3 *.wav *.flac *.aac *.ogg *.m4a *.wma"),
    ("All files", "*.*"),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Audio Asset Creator")
        self.resizable(False, False)
        self._file_path = tk.StringVar()
        self._transcribe = tk.BooleanVar()
        self._status = tk.StringVar()
        self._build_ui()
        apputils.install_hook(lambda: self)

    def _build_ui(self):
        file_frame = tk.Frame(self, padx=16, pady=16)
        file_frame.pack(fill="x")

        tk.Label(file_frame, text="Audio File:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        tk.Entry(file_frame, textvariable=self._file_path, width=48, state="readonly").grid(row=0, column=1)
        tk.Button(file_frame, text="Browse", command=self._browse).grid(row=0, column=2, padx=(8, 0))

        tk.Checkbutton(
            self,
            text="Transcribe lyrics",
            variable=self._transcribe,
        ).pack(anchor="w", padx=16)

        self._generate_btn = tk.Button(
            self, text="Generate", command=self._generate, padx=20, pady=6
        )
        self._generate_btn.pack(pady=(8, 6))

        self._progress_frame = tk.Frame(self, height=20)
        self._progress_frame.pack(fill="x", padx=16, pady=(0, 4))
        self._progress_frame.pack_propagate(False)

        self._progress = ttk.Progressbar(self._progress_frame, mode="determinate", maximum=100)

        tk.Label(self, textvariable=self._status, fg="gray").pack(pady=(0, 12))

    def _browse(self):
        path = filedialog.askopenfilename(filetypes=AUDIO_FILETYPES)
        if path:
            self._file_path.set(path)

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

        def on_progress(fraction):
            self.after(0, lambda: self._update_progress(int(fraction * 100)))

        try:
            out = save(path, transcribe=transcribing, progress_callback=on_progress if transcribing else None)
            self.after(0, lambda: self._on_done(out))
        except Exception as e:
            self.after(0, lambda: self._on_error(e))

    def _update_progress(self, value: int):
        self._progress["value"] = value

    def _on_done(self, out: str):
        self._update_progress(100)
        self._set_busy(False)
        from tkinter import messagebox
        messagebox.showinfo("Done", f"Asset saved to:\n{out}")

    def _on_error(self, exc: Exception):
        self._set_busy(False)
        apputils.show(self, exc, context="generate")

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


if __name__ == "__main__":
    App().mainloop()
