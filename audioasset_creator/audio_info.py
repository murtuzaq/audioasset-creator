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
    abs_path = os.path.abspath(audio_path)
    stat = os.stat(abs_path)
    name = os.path.basename(abs_path)
    ext = os.path.splitext(name)[1].lower().lstrip(".")

    duration = 0.0
    audio = MutagenFile(abs_path)
    if audio and audio.info:
        duration = round(audio.info.length, 3)

    return {
        "header": {
            "creator": "audioasset-creator",
            "version": _version(),
        },
        "audio_path": abs_path,
        "file_name": name,
        "file_type": ext,
        "size_bytes": stat.st_size,
        "duration_seconds": duration,
    }


def save(
    audio_path: str,
    transcribe: bool = False,
    transcribe_increment: float = 5.0,
    output_dir: str | None = None,
    progress_callback=None,
) -> str:
    info = extract(audio_path)
    if transcribe:
        from .transcriber import transcribe as do_transcribe
        info["header"]["lyric_increment_seconds"] = transcribe_increment
        info["lyrics"] = do_transcribe(
            audio_path,
            increment=transcribe_increment,
            progress_callback=progress_callback,
        )
    base = os.path.splitext(os.path.basename(audio_path))[0]
    out_dir = output_dir or os.path.dirname(os.path.abspath(audio_path))
    out_path = os.path.join(out_dir, base + ".info")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    return out_path
