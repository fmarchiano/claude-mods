"""Run: python3 mods/voice/hooks/test_voice.py"""
import json
import tempfile
from pathlib import Path

import voice

assert voice.extract_speak("x <speak>old</speak> y <speak>\n new \n</speak>") == "new"
assert voice.extract_speak("no tag") is None

rows = [
    {"type": "user", "message": {"content": "earlier prompt"}},
    {"type": "assistant", "message": {"content": [{"type": "text", "text": "stale <speak>no</speak>"}]}},
    {"type": "user", "message": {"content": "real prompt"}},
    {"type": "assistant", "message": {"content": [{"type": "text", "text": "a"}, {"type": "tool_use"}]}},
    {"type": "user", "message": {"content": [{"type": "tool_result"}]}},
    {"type": "assistant", "message": {"content": [{"type": "text", "text": "b <speak>yes</speak>"}]}},
]
with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
    f.write("\n".join(map(json.dumps, rows)))
text = voice.last_assistant_text(f.name)
assert text == "a\nb <speak>yes</speak>", text
assert voice.extract_speak(text) == "yes"
Path(f.name).unlink()
print("ok")
