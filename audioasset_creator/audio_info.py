import os
import json
from mutagen import File as MutagenFile


def extract(audio_path: str) -> dict:
    stat = os.stat(audio_path)
    name = os.path.basename(audio_path)
    ext = os.path.splitext(name)[1].lower().lstrip(".")

    duration = 0.0
    audio = MutagenFile(audio_path)
    if audio and audio.info:
        duration = round(audio.info.length, 3)

    return {
        "file_name": name,
        "file_type": ext,
        "size_bytes": stat.st_size,
        "duration_seconds": duration,
    }


def save(audio_path: str) -> str:
    info = extract(audio_path)
    out_path = os.path.splitext(audio_path)[0] + ".json"
    with open(out_path, "w") as f:
        json.dump(info, f, indent=2)
    return out_path
