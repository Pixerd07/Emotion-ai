def combine(audio, text):
    audio_label = audio.get("label", "neutral")
    text_label = text.get("label", "NEUTRAL")
    audio_stress = float(audio.get("stress_score", 0.0))
    text_risk = float(text.get("risk_score", 0.0))

    combined_risk = min(1.0, round((audio_stress * 0.45) + (text_risk * 0.55), 3))

    if text_label == "NEGATIVE" and audio_label in ["angry", "sad"]:
        final_emotion = "high_distress"
        reason = "Negative language and stressed voice detected"
    elif text_label == "NEGATIVE":
        final_emotion = "distressed"
        reason = "Negative language detected"
    elif text_label == "POSITIVE" and audio_label in ["angry", "sad"]:
        final_emotion = "emotional_mismatch"
        reason = "Words sound positive but tone sounds strained"
    elif audio_label == "sad":
        final_emotion = "low_mood"
        reason = "Voice tone suggests low mood"
    elif audio_label == "angry":
        final_emotion = "agitated"
        reason = "Voice tone sounds agitated"
    else:
        final_emotion = "neutral"
        reason = "No strong negative cues detected"

    should_console = final_emotion in {
        "high_distress",
        "distressed",
        "emotional_mismatch",
        "low_mood",
        "agitated",
    }

    return {
        "final_emotion": final_emotion,
        "combined_risk": combined_risk,
        "reason": reason,
        "should_console": should_console,
    }
