def transcribe(audio_path: str, increment: float = 5.0, progress_callback=None) -> dict:
    import sys
    import tqdm as _tqdm_mod
    import whisper
    import whisper.transcribe
    _wt = sys.modules["whisper.transcribe"]

    model = whisper.load_model("base")
    _original_tqdm_module = _wt.tqdm

    if progress_callback:
        class _ProgressTqdm:
            def __init__(self, iterable=None, *args, **kwargs):
                self._iterable = iterable if iterable is not None else []
                self.total = kwargs.get("total") or getattr(iterable, "__len__", lambda: None)()
                self.n = 0

            def __iter__(self):
                for item in self._iterable:
                    yield item
                    self.n += 1
                    if self.total:
                        progress_callback(self.n / self.total)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def update(self, n=1):
                self.n += n
                if self.total:
                    progress_callback(self.n / self.total)

            def set_postfix(self, *args, **kwargs):
                pass

        class _TqdmProxy:
            def __getattr__(self, name):
                return getattr(_tqdm_mod, name)

        proxy = _TqdmProxy()
        proxy.tqdm = _ProgressTqdm
        _wt.tqdm = proxy

    try:
        result = model.transcribe(audio_path, fp16=False, word_timestamps=True, verbose=False)
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg not found. Install it and ensure it is on your PATH.\n"
            "Windows: winget install ffmpeg  (then restart your terminal)"
        )
    finally:
        _wt.tqdm = _original_tqdm_module

    return {
        "text": result["text"].strip(),
        "cues": _build_cues(result["segments"], increment),
    }


def _build_cues(segments: list, increment: float) -> list:
    buckets: dict[int, list[str]] = {}
    for seg in segments:
        for w in seg.get("words", []):
            idx = int(w["start"] / increment)
            buckets.setdefault(idx, []).append(w["word"].strip())

    return [
        {"start": round(idx * increment, 3), "text": " ".join(words)}
        for idx, words in sorted(buckets.items())
    ]
