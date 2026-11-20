#!/usr/bin/env python3
"""claude-voice: speak Claude's <speak> block on whatever device has the voice page open.

Hooks (stdin = hook JSON):  prompt | stop | notify
User commands:              on | off | setup [topic]
"""
import json
import os
import re
import secrets
import sys
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("CLAUDE_VOICE_HOME", Path.home() / ".config" / "claude-voice"))
TOPIC_FILE = HOME / "topic"
ON_DIR = HOME / "on"
PAGE_URL = "https://fmarchiano.github.io/claude-mods/mods/voice/page/"
NTFY = os.environ.get("CLAUDE_VOICE_NTFY", "https://ntfy.sh")

SPEAK_RULE = (
    "Voice mode is on: the person is listening, likely walking, not reading. "
    "End your reply with a <speak>...</speak> block: natural spoken English, 2-5 sentences, "
    "no code, paths, markdown or lists; say what you did or found and what you need from them. "
    "If you need a decision, end the block with a clear question."
)


def topic():
    try:
        return TOPIC_FILE.read_text().strip() or None
    except OSError:
        return None


def post(text):
    t = topic()
    if not t or not text:
        return
    try:
        req = urllib.request.Request(f"{NTFY}/{t}", data=text.encode(), method="POST")
        urllib.request.urlopen(req, timeout=5).close()
    except Exception as e:  # never break the session over audio
        print(f"claude-voice: post failed: {e}", file=sys.stderr)


def is_on(sid):
    return bool(sid) and (ON_DIR / sid).exists()


def extract_speak(text):
    found = re.findall(r"<speak>(.*?)</speak>", text or "", re.S)
    return found[-1].strip() if found else None


def last_assistant_text(transcript_path):
    """Text of the assistant messages since the last real user prompt."""
    try:
        lines = Path(transcript_path).read_text().splitlines()
    except OSError:
        return ""
    parts = []
    for line in reversed(lines):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        content = (e.get("message") or {}).get("content")
        if e.get("type") == "user":
            is_tool_result = isinstance(content, list) and any(
                isinstance(c, dict) and c.get("type") == "tool_result" for c in content)
            if not is_tool_result:
                break
        elif e.get("type") == "assistant" and isinstance(content, list):
            parts += [c.get("text", "") for c in reversed(content) if c.get("type") == "text"]
    return "\n".join(reversed(parts))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")

    if cmd == "setup":
        HOME.mkdir(parents=True, exist_ok=True)
        if len(sys.argv) > 2:
            TOPIC_FILE.write_text(sys.argv[2].strip() + "\n")
        elif not topic():
            TOPIC_FILE.write_text(secrets.token_hex(16) + "\n")
        TOPIC_FILE.chmod(0o600)
        t = topic()
        print(f"Topic saved in {TOPIC_FILE}")
        print(f"Bookmark on each device: {PAGE_URL}#{t}")
        print(f"On other hosts run: /voice setup {t}")
        return
    if cmd in ("on", "off"):
        if not sid:
            sys.exit("claude-voice: CLAUDE_CODE_SESSION_ID not set; run this from inside Claude Code")
        if cmd == "on" and not topic():
            sys.exit("claude-voice: no topic yet; run /voice setup first")
        ON_DIR.mkdir(parents=True, exist_ok=True)
        flag = ON_DIR / sid
        flag.touch() if cmd == "on" else flag.unlink(missing_ok=True)
        print(f"Voice {cmd} for this session.")
        return

    data = json.load(sys.stdin)
    if not is_on(data.get("session_id")):
        return
    if cmd == "prompt":
        post("STOP")
        print(SPEAK_RULE)  # stdout of UserPromptSubmit is added to Claude's context
    elif cmd == "stop":
        text = data.get("last_assistant_message") or last_assistant_text(data.get("transcript_path", ""))
        post(extract_speak(text))
    elif cmd == "notify":
        post(data.get("message"))


if __name__ == "__main__":
    main()
