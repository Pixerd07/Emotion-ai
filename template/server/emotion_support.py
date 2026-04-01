from services import fusion, response, text_emotion

_NEUTRAL_AUDIO = {
    "label": "neutral",
    "intensity": "low",
    "energy": 0.0,
    "pitch": 0.0,
    "stress_score": 0.0,
}


def transcript_to_reply(text: str) -> str:
    cleaned = (text or "").strip()
    te = text_emotion.detect(cleaned)
    fused = fusion.combine(_NEUTRAL_AUDIO, te)
    return response.generate(cleaned, fused)
