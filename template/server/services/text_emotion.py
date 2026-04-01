from transformers import pipeline

classifier = pipeline(
    "sentiment-analysis",
    model="distilbert/distilbert-base-uncased-finetuned-sst-2-english",
)


def detect(text):
    cleaned_text = (text or "").strip()
    if not cleaned_text:
        return {
            "label": "NEUTRAL",
            "score": 0.0,
            "mapped_emotion": "neutral",
            "risk_score": 0.0,
        }

    result = classifier(cleaned_text)[0]
    label = result.get("label", "NEUTRAL").upper()
    score = float(result.get("score", 0.0))

    if label == "NEGATIVE":
        mapped_emotion = "distress"
        risk_score = score
    elif label == "POSITIVE":
        mapped_emotion = "positive"
        risk_score = max(0.0, 1.0 - score) * 0.2
    else:
        mapped_emotion = "neutral"
        risk_score = 0.2

    return {
        "label": label,
        "score": round(score, 3),
        "mapped_emotion": mapped_emotion,
        "risk_score": round(risk_score, 3),
    }
