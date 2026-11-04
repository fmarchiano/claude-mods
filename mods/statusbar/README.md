# statusbar

A Claude Code status line that shows the model, the reasoning effort, how full the context window is, and how long the prompt cache has left.

```
Opus | effort:high | 🟢 ctx ████░░░░░░░░░░░|░░░░░ 40k/150k | cache ███████░░░ 41:12
```

- **ctx**: the live context size on a 300k scale, with a `|` marker at a 150k soft limit. 🟢 below 100k, 🟡 from 100k, 🔴 from 150k.
- **cache**: a countdown from the last main-thread response to the end of the prompt cache TTL (1h by default; set `cacheTtl` to `5m` in the plugin's options). It refills on every response and reads `expired` once the cache has lapsed.

The line refreshes every second.
