---
name: md_to_pdf
description: "Convert one or more Markdown files to PDF using pandoc + weasyprint in the `science` conda env (created automatically if missing), styled with the SeCore house style (Jost/Source Serif 4, monochrome, numbered sections, masthead). Trigger: user asks to convert markdown to PDF, export .md as PDF, or /md_to_pdf."
---

# /md_to_pdf

Convert Markdown file(s) to a PDF styled in the SeCore house style: A4, monochrome
ink-on-white, Jost for structure, Source Serif 4 for prose.

## Usage

```
/md_to_pdf <file1.md> [file2.md ...]
```

## What it does

Runs `scripts/convert.sh` which, per file:
1. Activates conda env `science` via `scripts/ensure_env.sh`, **creating that env from
   conda-forge if the machine does not have it yet** (first run only). Conda itself is
   discovered at runtime, so no path is hardcoded to any one machine.
2. The env carries `pandoc` and `weasyprint` (no LaTeX needed), plus `poppler` and
   `pymupdf` for the PDF-reading skills.
3. Pre-renders any ` ```mermaid ` fenced blocks to SVG via `scripts/render_mermaid.py`
   (uses kroki.io, needs network; cached under `<name>_diagrams/`).
4. Runs pandoc with `assets/template.html` (masthead + meta block) and
   `assets/secore.css` (the house style), through `--pdf-engine=weasyprint`.

The PDF is written next to the source as `<name>.pdf`, replacing any older one.
This skill never sends anything to the tablet.

### After converting: here or tablet (required, last step)

Ask the user with AskUserQuestion where the PDF should go:
- **Keep here only**: done; report the local path.
- **Also send to the tablet**: invoke the `to_tablet` skill on the new PDF(s). It
  asks for the tablet folder, pushes the file, and runs the open-decisions round.

Skip the question when the user already said in the request ("convert" alone
means here only; "send to the tablet" means invoke `to_tablet` straight after).

## Writing a source document

### Front matter → masthead and meta block

```yaml
---
title: "System Architecture Review"
doctype: "Technical Memo"
meta:
  - key: Author
    value: Fabio Marchiano
  - key: Date
    value: 2026-09-16
  - key: Status
    value: Draft
---
```

`title` becomes the H1 under the masthead; `doctype` renders top-right in the
masthead rule; `meta` becomes the two-column definition grid below it. All
three are optional — omit `meta` and the grid is skipped.

### Sections

Plain `##` headings are auto-numbered (`01`, `02`, ...) with a 1px rule
underneath. No manual numbering needed.

### Callouts

```markdown
::: callout
**Note.** Uncertainty here is stated plainly, not softened.
:::
```

The first bold run becomes the uppercase kicker label.

### Status and tags

```markdown
Delivery timeline: [Confirmed]{.status-confirmed}
Follow-up scope: [Open]{.status-open}

Owner tier: [Lead]{.tag-lead}  [Reserve]{.tag-reserve}
```

### Tinted lead rows in a table

```markdown
::: leads
| Item | Owner | Status |
|---|---|---|
| API gateway | Fabio | Confirmed |
| Cache layer | — | Open |
:::
```

Only the first body row is tinted, standard lead-row convention.

### Diagrams

Use a normal ` ```mermaid ` fenced block for any workflow, sequence, or state
diagram; it is rendered to SVG and dropped in centered, no manual image step.

```markdown
    ```mermaid
    flowchart TD
      A[Draft] --> B[Review]
      B --> C{Approved?}
      C -->|Yes| D[Publish]
      C -->|No| A
    ```
```

Prefer mermaid `flowchart`/`sequenceDiagram`/`stateDiagram-v2` over prose
whenever a process has branches or handoffs, a diagram reads faster than a
paragraph of "first X, then if Y...".

## Style reference

- Page: A4, white, 0.75in print margin + 0.7in header/footer reserve (top/bottom),
  max content width 8.27in.
- Body: Source Serif 4, 14.5px / 1.62. Headings, labels, tables, captions, meta
  fields: Jost.
- Color is strictly monochrome: ink `#16181a`, secondary `#3a3e43`, muted `#8c9197`,
  rules `#d8dadd`, table borders `#e3e5e7`, borders `#c4c7ca`, fills `#f4f5f6`/`#f8f9fa`,
  page surround `#eceeef`.
- No em-dashes in generated prose; commas or "e.g." instead. State uncertainty
  plainly rather than softening it.

Edit `assets/secore.css` to adjust the look; edit `assets/template.html` to
change the masthead/meta structure. Both apply to every future conversion.

## Invocation

```bash
bash <this skill's base directory>/scripts/convert.sh <file1.md> [file2.md ...]
```
