import json
import math
import os
import tkinter as tk
from tkinter import messagebox


class LyricsEditor(tk.Toplevel):
    def __init__(
        self,
        parent,
        info_path: str,
        audio_path: str,
        increment: float,
        reference_transcript: str | None = None,
    ):
        super().__init__(parent)
        self.title("Lyrics Editor")
        self.resizable(True, True)
        self.grab_set()

        self._info_path = info_path
        self._audio_path = audio_path
        self._increment = increment
        self._reference = reference_transcript
        self._cue_vars: list[tk.StringVar] = []

        self._info = self._load_info()
        self._ensure_cues()

        self._build_ui()
        self.geometry("940x560" if reference_transcript else "520x560")

    def _load_info(self) -> dict:
        if os.path.exists(self._info_path):
            with open(self._info_path, "r", encoding="utf-8") as f:
                return json.load(f)
        from audioasset_creator.audio_info import extract
        return extract(self._audio_path)

    def _ensure_cues(self):
        cues = self._info.get("lyrics", {}).get("cues", [])
        if not cues:
            from mutagen import File as MutagenFile
            audio = MutagenFile(self._audio_path)
            duration = audio.info.length if audio and audio.info else 0.0
            slots = math.ceil(duration / self._increment) if duration > 0 else 0
            cues = [
                {"start": round(i * self._increment, 3), "text": ""}
                for i in range(slots)
            ]
            self._info.setdefault("header", {})["lyric_increment_seconds"] = self._increment
            self._info.setdefault("lyrics", {})["cues"] = cues

    def _build_ui(self):
        cues = self._info.get("lyrics", {}).get("cues", [])

        panels = tk.Frame(self)
        panels.pack(fill="both", expand=True, padx=12, pady=(12, 4))

        if self._reference:
            ref_frame = tk.LabelFrame(panels, text="Reference transcript")
            ref_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
            self._build_reference_panel(ref_frame)

        cue_frame = tk.LabelFrame(panels, text="Cues  —  edit to correct")
        cue_frame.pack(side="left", fill="both", expand=True)
        self._build_cue_panel(cue_frame, cues)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text="Save", command=self._save, padx=16, pady=4).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Cancel", command=self.destroy, padx=16, pady=4).pack(side="left", padx=4)

    def _build_reference_panel(self, parent):
        scrollbar = tk.Scrollbar(parent)
        scrollbar.pack(side="right", fill="y")
        text = tk.Text(
            parent,
            wrap="word",
            font=("Courier", 9),
            yscrollcommand=scrollbar.set,
            width=36,
        )
        text.pack(fill="both", expand=True)
        text.insert("1.0", self._reference)
        scrollbar.config(command=text.yview)

    def _build_cue_panel(self, parent, cues: list):
        scrollbar = tk.Scrollbar(parent, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        canvas = tk.Canvas(parent, yscrollcommand=scrollbar.set)
        canvas.pack(fill="both", expand=True)
        scrollbar.config(command=canvas.yview)

        inner = tk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

        tk.Label(inner, text="Start", width=8, font=("", 9, "bold"), anchor="e").grid(
            row=0, column=0, padx=(4, 2), pady=(4, 2)
        )
        tk.Label(inner, text="Lyrics", font=("", 9, "bold"), anchor="w").grid(
            row=0, column=1, padx=(2, 4), pady=(4, 2), sticky="w"
        )

        self._cue_vars = []
        for i, cue in enumerate(cues):
            tk.Label(inner, text=f"{cue['start']:.1f}s", width=8, anchor="e", fg="gray").grid(
                row=i + 1, column=0, padx=(4, 2), pady=2
            )
            var = tk.StringVar(value=cue["text"])
            tk.Entry(inner, textvariable=var, width=44).grid(
                row=i + 1, column=1, padx=(2, 4), pady=2, sticky="ew"
            )
            self._cue_vars.append(var)

        inner.columnconfigure(1, weight=1)

    def _save(self):
        cues = self._info.get("lyrics", {}).get("cues", [])
        for cue, var in zip(cues, self._cue_vars):
            cue["text"] = var.get().strip()
        with open(self._info_path, "w", encoding="utf-8") as f:
            json.dump(self._info, f, indent=2)
        messagebox.showinfo("Saved", f"Lyrics saved to:\n{self._info_path}", parent=self)
        self.destroy()
