def transcribe(audio_path: str) -> dict:
    import whisper
    model = whisper.load_model("base")
    try:
        result = model.transcribe(audio_path)
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg not found. Install it and ensure it is on your PATH.\n"
            "Windows: winget install ffmpeg  (then restart your terminal)"
        )
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
