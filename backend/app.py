from flask import Flask, request, jsonify
from flask_cors import CORS

from services import stt, audio_emotion, text_emotion, fusion, response

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def root():
    return jsonify(
        {
            "status": "ok",
            "message": "Emotion AI backend is running (REST fallback)",
            "routes": {"analyze": "POST /analyze", "analyze_text": "POST /analyze-text"},
        }
    )


def _analyze_text_pipeline(text, audio_emotion_input=None):
    audio_em = audio_emotion_input or {
        "label": "neutral",
        "intensity": "low",
        "energy": 0.0,
        "pitch": 0.0,
        "stress_score": 0.0,
    }
    text_em = text_emotion.detect(text)
    fused = fusion.combine(audio_em, text_em)
    reply = response.generate(text, fused)
    return {
        "text": text,
        "audio_emotion": audio_em,
        "text_emotion": text_em,
        "analysis": fused,
        "final_emotion": fused["final_emotion"],
        "response": reply,
    }


@app.route("/analyze", methods=["POST"])
def analyze():
    if "audio" not in request.files:
        return jsonify({"error": "Missing audio file"}), 400

    file = request.files["audio"]
    audio_bytes = file.read()
    if not audio_bytes:
        return jsonify({"error": "Empty audio payload"}), 400

    try:
        text = stt.convert(audio_bytes, file.filename)
        audio_em = audio_emotion.detect(audio_bytes, file.filename)
        payload = _analyze_text_pipeline(text, audio_emotion_input=audio_em)
        return jsonify(payload)
    except Exception as ex:
        return jsonify({"error": f"Analysis failed: {str(ex)}"}), 500


@app.route("/analyze-text", methods=["POST"])
def analyze_text():
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Missing text"}), 400

    try:
        payload = _analyze_text_pipeline(text)
        return jsonify(payload)
    except Exception as ex:
        return jsonify({"error": f"Text analysis failed: {str(ex)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
