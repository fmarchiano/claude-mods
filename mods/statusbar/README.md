# statusbar

A Claude Code status line that shows the model, the reasoning effort, how full the context window is, and how long the prompt cache has left.

```
Opus | effort:high | 🟢 ctx ████░░░░░░░░░░░|░░░░░ 40k/150k | cache ███████░░░ 41:12
```

- **ctx**: the live context size on a 300k scale, with a `|` marker at a 150k soft limit. 🟢 below 100k, 🟡 from 100k, 🔴 from 150k.
- **cache**: a countdown from the last main-thread response to the end of the 1h prompt cache. It refills on every response and reads `expired` once the cache has lapsed.

## Cache handoff

When the session has been idle until 5 minutes remain on the cache — and context exceeds 30k tokens — the mod submits a handoff prompt via `$.prompt.submit`. The handoff document is saved to `/tmp/claude-handoff-<session id>.md`. Once written, the mod runs `/clear` and fills the prompt with `Read the handoff at <path> and continue from it.` — pressing Enter continues in a fresh session. `/resume` brings the old conversation back.

Fires once per idle stretch; re-arms when you send a message.

The line refreshes every second.
