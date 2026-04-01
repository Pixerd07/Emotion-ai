def generate(text, analysis):
    final_emotion = analysis.get("final_emotion", "neutral")
    should_console = analysis.get("should_console", False)

    responses = {
        "high_distress": (
            "I hear that this is really heavy right now. "
            "Take a slow breath with me: inhale 4s, hold 4s, exhale 6s. "
            "If you want, tell me what feels hardest at this moment."
        ),
        "distressed": (
            "I'm sorry you are going through this. "
            "You are not alone. Want to share what triggered this feeling?"
        ),
        "emotional_mismatch": (
            "Your words sound okay, but your tone seems tense. "
            "It is completely fine to admit you are not okay."
        ),
        "low_mood": (
            "You sound a bit low right now. "
            "A short break, water, and one small next step might help."
        ),
        "agitated": (
            "You sound frustrated. "
            "Let's pause for 20 seconds and reset before continuing."
        ),
        "neutral": "You sound steady right now. I am here if you want to talk.",
    }

    if should_console:
        return responses.get(final_emotion, "I am here with you. We can take this one step at a time.")
    return responses["neutral"]
