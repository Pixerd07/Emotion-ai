import os
import tempfile
from pathlib import Path

import librosa
import numpy as np


def _safe_suffix(source_name):
    suffix = Path(source_name or "").suffix.lower()
    if suffix in {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".mp4"}:
        return suffix
    return ".wav"


def detect(audio_bytes, source_name=None):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=_safe_suffix(source_name), delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        y, sr = librosa.load(temp_path)

        energy = float(np.mean(librosa.feature.rms(y=y)))
        pitch = float(np.mean(librosa.yin(y, fmin=50, fmax=300)))

        if energy > 0.12 and pitch > 190:
            label = "angry"
            intensity = "high"
        elif energy < 0.04:
            label = "sad"
            intensity = "medium"
        else:
            label = "neutral"
            intensity = "low"

        stress_score = min(1.0, max(0.0, ((energy - 0.03) * 4.0) + ((pitch - 140) / 200)))

        return {
            "label": label,
            "intensity": intensity,
            "energy": round(energy, 4),
            "pitch": round(pitch, 2),
            "stress_score": round(stress_score, 3),
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)