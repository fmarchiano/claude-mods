# claude-mods

My Claude Code mods and skills, as one plugin marketplace so every machine gets the same setup.

| Plugin | What it is |
| --- | --- |
| `statusbar` | Status line: model, effort, context bar (150k soft limit on a 300k scale), prompt-cache countdown |
| `fab-skills` | Skills: `md_to_pdf`, `to_tablet` |

## Install

The repository is private: the machine needs a git credential for github.com first (an SSH key, or `gh auth login` then `gh auth setup-git`).

At the prompt of a terminal session:

```
/plugin install statusbar --marketplace fmarchiano/claude-mods
/plugin install fab-skills --marketplace fmarchiano/claude-mods
```

From a shell:

```
claude plugin install statusbar --marketplace fmarchiano/claude-mods
claude plugin install fab-skills --marketplace fmarchiano/claude-mods
```

Answer `y` to add the marketplace, then pick the user scope.

## Update

```
claude plugin marketplace update fab-mods
claude plugin update statusbar
```

then `/reload-plugins` in a running session.
