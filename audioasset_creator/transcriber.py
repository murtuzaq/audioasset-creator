import difflib
import re

_SIMILARITY_THRESHOLD = 0.2


def transcribe(
    audio_path: str,
    increment: float = 5.0,
    known_transcript: str | None = None,
    progress_callback=None,
) -> dict:
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
        result = model.transcribe(
            audio_path,
            fp16=False,
            word_timestamps=True,
            verbose=False,
            initial_prompt=known_transcript,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg not found. Install it and ensure it is on your PATH.\n"
            "Windows: winget install ffmpeg  (then restart your terminal)"
        )
    finally:
        _wt.tqdm = _original_tqdm_module

    if known_transcript:
        _check_similarity(known_transcript, result["text"])

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


def _normalize(text: str) -> list[str]:
    return re.sub(r"[^\w\s]", "", text.lower()).split()


def _check_similarity(known: str, transcribed: str) -> None:
    known_words = set(_normalize(known))
    transcribed_words = set(_normalize(transcribed))
    union = known_words | transcribed_words
    if not union:
        return
    jaccard = len(known_words & transcribed_words) / len(union)
    if jaccard < _SIMILARITY_THRESHOLD:
        raise ValueError(
            f"The provided transcript doesn't appear to match the audio "
            f"(word overlap: {jaccard:.0%}). Please check that you uploaded the correct file."
        )
