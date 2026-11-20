# voice

Hands-free loop for planning while walking: you dictate (Wispr Flow or anything that types), Claude works, and a web page on whatever device you have open reads the reply aloud.

```
Claude Code hook ──POST──► ntfy.sh/<secret topic> ──SSE──► voice page (any browser) ──speechSynthesis──► earbuds
```

## Setup

1. Install on each Claude host: `/plugin install voice@fab-mods`
2. On the first host: `/voice setup`. It creates a random topic in `~/.config/claude-voice/topic` and prints a bookmark URL and the line for the other hosts.
3. On the other hosts: `/voice setup <topic>`.
4. On each device, open the bookmark URL and tap **Tap to start listening**. Microsoft Edge has the most natural voices; pick one from the dropdown.

The topic is the only key: anyone who knows it can read or post. It never goes in this repo, and the URL keeps it in the `#fragment`, which browsers don't send to the server.

## Use

- `/voice on` - this session speaks. New and resumed sessions start silent.
- `/voice off` - silent again.

While on, Claude ends each reply with a short `<speak>` block in plain English, and only that block is spoken. Sending a new prompt stops playback. Permission prompts and "waiting for input" alerts are spoken too.

The page keeps the screen awake so the browser doesn't pause it. Whichever device has the page open speaks.

## Files

- `hooks/voice.py` - the hooks (`prompt`, `stop`, `notify`) and the `/voice` subcommands (`on`, `off`, `setup`). Run `python3 hooks/test_voice.py` to check it.
- `page/index.html` - the listening page, served by GitHub Pages.
