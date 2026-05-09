# audioasset-creator

A Python tool for generating audio asset info files (`.info`) from audio files. Can be used as a standalone GUI/CLI app or imported as a library.

## Requirements

### Python
Python 3.10 or higher.

### System dependency — ffmpeg
Whisper (lyrics transcription) requires `ffmpeg` to be installed and available on your `PATH`.

**Windows (winget):**
```
winget install ffmpeg
```

**Windows (choco):**
```
choco install ffmpeg
```

After installing, restart your terminal and verify with:
```
ffmpeg -version
```

### Python dependencies
Install all Python packages:
```
pip install -r requirements.txt
```

| Package | Version | Purpose |
|---|---|---|
| `mutagen` | >=1.47.0 | Audio metadata (duration, format) |
| `openai-whisper` | >=20231117 | Lyrics transcription |

## Usage

### GUI
```
python app_gui.py
```

### CLI
```
python app_cli.py <path-to-audio-file>
```

## Output

Generates a `.info` file alongside the audio file:

```json
{
  "header": {
    "creator": "audioasset-creator",
    "version": "v0.1.0"
  },
  "file_name": "track.mp3",
  "file_type": "mp3",
  "size_bytes": 4823040,
  "duration_seconds": 201.453,
  "lyrics": {
    "text": "Full transcript...",
    "segments": [
      { "start": 0.0, "end": 3.42, "text": "First line..." }
    ]
  }
}
```

`lyrics` is only included when **Transcribe lyrics** is checked (GUI) or the transcribe flag is set (library).
