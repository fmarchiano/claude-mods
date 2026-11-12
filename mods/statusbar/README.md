# statusbar

A Claude Code status line that shows the model, the reasoning effort, how full the context window is, and how long the prompt cache has left.

```
Opus | effort:high | 🟢 ctx ████░░░░░░░░░░░|░░░░░ 40k/150k | cache ███████░░░ 41:12
```

- **ctx**: the live context size on a 300k scale, with a `|` marker at a 150k soft limit. 🟢 below 100k, 🟡 from 100k, 🔴 from 150k.
- **cache**: a countdown from the last main-thread response to the end of the 1h prompt cache. It refills on every response and reads `expired` once the cache has lapsed.

## Handoff before the cache lapses

When the session has sat idle until 10 minutes are left on the cache, the mod runs Matt Pocock's `handoff` skill (from `mattpocock-skills`; a built-in prompt with the same instructions when that plugin is missing) while the cache is still warm. The document is saved to `/tmp/claude-handoff-<session id>.md`. Once it is written the mod runs `/clear` and fills the prompt with `Read the handoff at <path> and continue from it.`, so pressing Enter continues in a fresh, cheap session. `/resume` brings the old conversation back.

It hands off once per idle stretch: it waits for your next message before it can fire again.

The line refreshes every second.
