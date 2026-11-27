---
name: md_to_pdf
description: "Convert Markdown to PDF for any document: reports, memos, cover/motivation letters, notes. Default style `cv` matches Fabio's CV (Jost, forest-green accent, name masthead); `--style secore` gives the SeCore monochrome house style. Trigger: user asks to convert markdown to PDF, export .md as PDF, make a PDF in my CV style, or /md_to_pdf."
---

# /md_to_pdf

Convert Markdown file(s) to an A4 PDF. Two styles, one source format:

- **`cv` (default)**: Fabio's CV look. Jost throughout, ink `#17211d` on white, one
  forest-green accent `#1f5c4d`, name + role + contacts masthead. Use for everything
  unless the document is a SeCore deliverable.
- **`secore`**: SeCore house style. Monochrome, Jost + Source Serif 4, numbered
  sections, SeCore wordmark. Use only when the user says the document is for SeCore.

When the user asks for "the style of my CV" or a letter, that is `cv`: adjust
`assets/cv.css` rather than writing a one-off converter.

## Usage

```
/md_to_pdf [--style cv|secore] <file1.md> [file2.md ...]
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
4. Runs pandoc with `assets/<style>.html` (template) and `assets/<style>.css`,
   through `--pdf-engine=weasyprint`.

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

### Front matter, `cv` style

All fields optional. The masthead defaults to Fabio's name, role and public links;
override any of them per document.

```yaml
---
name: "Fabio Marchianò, PhD"          # masthead H1 (default puts PhD in green)
role: "Senior Bioinformatics Scientist / Engineer"
contact: ["email@example.com", "linkedin.com/in/fmarchiano", "github.com/fmarchiano"]
recipient:                            # letters: address block, left
  - Prof. Jane Doe
  - Institute, City
date: 27/11/2026                      # right, opposite the recipient
subject: "Application for the Data Scientist position"   # green kicker
title: "Report title"                 # reports: big H1 under masthead
meta: [{key: Status, value: Draft}]   # two-column grid, CV skills look
---
```

A letter's sign-off goes in a `closing` div, with `\` for the line break:

```markdown
::: closing
Kind regards,\
**Fabio Marchianò, PhD**
:::
```

In `cv`, `##` headings are green uppercase kickers (not numbered), `###` are bold
ink subheads, a paragraph's leading **bold** run turns green, and bullet lists get
the CV's green bar with › markers.

### Front matter, `secore` style

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

### Sections (`secore`)

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

### `cv`

- Page: A4, 13/17mm margins, page counter bottom-right from page 2.
- Jost only: body 12.6px / 1.42, name 34px/500, kickers 10.5px/700 tracked .18em.
- Colors: ink `#17211d`, body `#2e352f`, secondary `#3a423b`, muted `#5c665f`,
  faint `#9aa39c`, accent `#1f5c4d`, rules `#e3e7e4`, fill `#f3f5f3`.
- Letters should fit one page; if one spills a few lines, tighten the prose first.

### `secore`

- Page: A4, white, 0.75in print margin + 0.7in header/footer reserve (top/bottom),
  max content width 8.27in.
- Body: Source Serif 4, 14.5px / 1.62. Headings, labels, tables, captions, meta
  fields: Jost.
- Color is strictly monochrome: ink `#16181a`, secondary `#3a3e43`, muted `#8c9197`,
  rules `#d8dadd`, table borders `#e3e5e7`, borders `#c4c7ca`, fills `#f4f5f6`/`#f8f9fa`,
  page surround `#eceeef`.
- No em-dashes in generated prose; commas or "e.g." instead. State uncertainty
  plainly rather than softening it.

Edit `assets/<style>.css` to adjust a look; edit `assets/<style>.html` to change
its masthead/meta structure. Both apply to every future conversion.

## Invocation

```bash
bash <this skill's base directory>/scripts/convert.sh [--style cv|secore] <file1.md> [file2.md ...]
```
