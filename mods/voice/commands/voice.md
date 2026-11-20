---
description: Voice mode - on | off | setup [topic]
argument-hint: on | off | setup [topic]
allowed-tools: Bash(python3:*)
---

Run exactly this with the Bash tool and report its output in one line:

```
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/voice.py" $ARGUMENTS
```

If the argument was `on`, end your reply with `<speak>Voice is on. I'm listening.</speak>`.
