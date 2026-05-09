import os
import json
import subprocess
from mutagen import File as MutagenFile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _version() -> str:
    try:
        v = subprocess.check_output(
            ["git", "describe", "--tags"],
            cwd=_REPO_ROOT,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return v if v else "v0.1.0"
    except Exception:
        return "v0.1.0"


def extract(audio_path: str) -> dict:
    stat = os.stat(audio_path)
    name = os.path.basename(audio_path)
    ext = os.path.splitext(name)[1].lower().lstrip(".")

    duration = 0.0
    audio = MutagenFile(audio_path)
    if audio and audio.info:
        duration = round(audio.info.length, 3)

    return {
        "header": {
            "creator": "audioasset-creator",
            "version": _version(),
        },
        "file_name": name,
        "file_type": ext,
        "size_bytes": stat.st_size,
        "duration_seconds": duration,
    }


def save(
    audio_path: str,
    transcribe: bool = False,
    transcribe_increment: float = 5.0,
    known_transcript: str | None = None,
    progress_callback=None,
) -> str:
    info = extract(audio_path)
    if transcribe:
        from .transcriber import transcribe as do_transcribe
        info["header"]["lyric_increment_seconds"] = transcribe_increment
        info["lyrics"] = do_transcribe(
            audio_path,
            increment=transcribe_increment,
            known_transcript=known_transcript,
            progress_callback=progress_callback,
        )
    out_path = os.path.splitext(audio_path)[0] + ".info"
    with open(out_path, "w") as f:
        json.dump(info, f, indent=2)
    return out_path
