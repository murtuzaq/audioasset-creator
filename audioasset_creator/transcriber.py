def transcribe(audio_path: str, progress_callback=None) -> dict:
    import sys
    import whisper
    import whisper.transcribe  # ensure submodule is loaded into sys.modules
    _wt = sys.modules["whisper.transcribe"]

    model = whisper.load_model("base")
    _original_tqdm = _wt.tqdm

    if progress_callback:
        class _TrackedTqdm(_original_tqdm):
            def update(self, n=1):
                super().update(n)
                if self.total and self.total > 0:
                    progress_callback(self.n / self.total)
        _wt.tqdm = _TrackedTqdm

    try:
        result = model.transcribe(audio_path)
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg not found. Install it and ensure it is on your PATH.\n"
            "Windows: winget install ffmpeg  (then restart your terminal)"
        )
    finally:
        _wt.tqdm = _original_tqdm

    return {
        "text": result["text"].strip(),
        "segments": [
            {
                "start": round(s["start"], 3),
                "end": round(s["end"], 3),
                "text": s["text"].strip(),
            }
            for s in result["segments"]
        ],
    }
