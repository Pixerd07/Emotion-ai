import os
import tempfile
from pathlib import Path

import whisper

model = whisper.load_model("tiny")


def _safe_suffix(source_name):
    suffix = Path(source_name or "").suffix.lower()
    if suffix in {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".mp4"}:
        return suffix
    return ".wav"


def convert(audio_bytes, source_name=None):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=_safe_suffix(source_name), delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        result = model.transcribe(temp_path)
        return result.get("text", "").strip()
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)