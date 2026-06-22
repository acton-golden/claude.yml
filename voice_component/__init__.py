import os
import streamlit.components.v1 as components

_FRONTEND = os.path.join(os.path.dirname(__file__), "frontend")
_func = components.declare_component("voice_interview", path=_FRONTEND)

# Voice personality per reporter — rate (speed) and pitch
VOICES = {
    "devil":    {"rate": 0.82, "pitch": 0.85},  # Deep, deliberate
    "buddy":    {"rate": 1.0,  "pitch": 1.15},  # Warm, upbeat
    "hombre":   {"rate": 1.08, "pitch": 1.0},   # Smooth, confident
    "cobra":    {"rate": 0.68, "pitch": 0.75},  # Cold, slow
    "traveler": {"rate": 0.88, "pitch": 1.05},  # Measured, grave
}


def voice_turn(question: str, reporter_name: str, reporter_key: str, key: str = None):
    """
    Renders TTS + STT component.
    Speaks the question automatically, then opens mic for user answer.
    Returns transcript string when user submits, or None while waiting.
    """
    v = VOICES.get(reporter_key, {"rate": 0.9, "pitch": 1.0})
    return _func(
        question=question,
        reporter_name=reporter_name,
        rate=v["rate"],
        pitch=v["pitch"],
        key=key,
        default=None,
    )
