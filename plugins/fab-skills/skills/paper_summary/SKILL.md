---
name: paper-summary
description: "Summarize a scientific paper PDF into a graphical abstract PDF: citation header, a background split into Problem / Approach / Solution, a BioRender-drawn methods scene, key finding. Runs in the `science` conda env, created automatically if missing. Trigger: summarize paper, paper summary, graphical abstract, summarize this PDF, paper overview."
---

# Paper Summary

Produce a short graphical abstract PDF from a scientific paper PDF: typically 1 to 3 pages,
depending on how many stages the paper's pipeline has. Do not pad to fill a page, and do not
drop real method detail just to save one.

## Input

A file path to a PDF. If the user doesn't provide one, ask for it.

## Steps

### 0. Make the `science` env available

All tooling for this skill lives in the `science` conda env. Activate it, creating it
if this machine does not have it (first run only, several minutes):

```bash
source "<this skill's base directory>/../../scripts/ensure_env.sh"
```

That script finds conda at runtime, so it works unchanged on any machine. The env
provides `poppler` (`pdftoppm`/`pdftotext`, which the Read tool needs to open PDFs)
and `pymupdf`. Put its `bin` on PATH before reading a PDF:

```bash
export PATH="$CONDA_PREFIX/bin:$PATH"
```

Without `pdftoppm` the Read tool fails on PDFs with
`pdftoppm is not installed`. If the env cannot be created (no network), fall back to
text extraction and say so in your report rather than silently degrading:

```bash
python -c "import fitz,sys; d=fitz.open(sys.argv[1]); print(chr(12).join(p.get_text() for p in d))" paper.pdf
```

### 1. Read the paper strategically

Use the Read tool on the PDF. Read in page-range chunks (max 20 pages per call).
Target these sections, skipping only the references:

- **First 3 pages**: title, authors, journal, DOI, abstract, start of introduction.
- **Introduction** (remaining pages if it continues) — this gives you **Problem**.
- **Results**: read for the headline numbers, the ones the Solution paragraph will
  quote (yields, accuracy, precision, affinities, effect sizes). Skim the
  figure-by-figure detail, but do not skip the section: Solution is the results.
- **Methods / Materials and Methods**: read fully — this drives both the BioRender
  scene and the definition list under it.
- **Discussion / Conclusion**: read fully.

Identify page ranges from the table of contents or section headers in the first read.

Completion: you can answer all four output sections below from what you read.

### 2. Write the summary markdown

Write a file `<original_stem>_summary.md` in the same directory as the input PDF.

Use this structure exactly:

```markdown
---
title: "<Paper title>"
doctype: "Paper Summary"
meta:
  - key: Authors
    value: "<First Author> et al."
  - key: Journal
    value: "<Journal>, <Year>"
  - key: DOI
    value: "<DOI or 'not found'>"
---

## Background

**Problem.** <The question the paper sets out to answer and why it was still open:
what people needed to know, and what the existing methods or results could not give
them. From the introduction. 2–4 sentences.>

**Approach.** <How the authors went after that question: the idea or insight the work
turns on, stated at the level of strategy, not protocol. The step-by-step belongs in
the Methods diagram below, so do not repeat kits or reagents here. 1–3 sentences.>

**Solution.** <The results: what they actually found out. Report the findings with
the numbers that matter (yields, accuracy, precision, affinities, effect sizes),
taken from the results section. Facts first, not implications: state what the data
showed, and only then, if it is needed, one short clause on what it means. 2–4
sentences.>

## Methods

![<One short sentence naming what the scene shows. This prints as the visible
caption under the figure, so keep it to one line, not a list of every object.>](<original_stem>_figure.jpg)

<One sentence per stage of the scene explaining the specific technique, kit, or
tool used. Use a definition list:>

**<Stage 1 label>**
: <detail>

**<Stage 2 label>**
: <detail>

**<Stage 3 label>**
: <detail>

**<Stage 4 label>**
: <detail>

**<Stage 5 label>**
: <detail>

::: callout
**Key Finding.** <One sentence: the single most important result or conclusion.>
:::
```

### The three Background paragraphs

Background is always three labelled paragraphs, in this order, with these exact
bold labels: **Problem.**, **Approach.**, **Solution.** They answer, in turn:

1. **Problem** — what question needed answering, and why it was still open.
2. **Approach** — how the authors went about answering it.
3. **Solution** — the results: what they found out.

Never merge them into a single block of prose, never reorder them, and never drop
one because the paper buries it. Keep the whole section under ~12 sentences, and
use no jargon the abstract doesn't use. If the paper only partly answers its own
question, say so in the Solution rather than writing it as settled.

### The Methods scene

The methods are shown as one illustrated scene, not a boxed flowchart. Generate it
with BioRender (step 3) and reference it as `<original_stem>_figure.jpg`. Keep the
definition list under the image: the drawing carries the shape of the method, the
list carries the reagents, kits and tools, which no illustration can show.

Adapt the stage count to the actual pipeline — more stages if the paper has more
wet-lab or bioinformatics steps, fewer if it is simpler. Five is a starting shape,
not a constraint.

Completion: the markdown file exists, references the figure, and uses md_to_pdf
frontmatter.

### 3. Draw the graphical abstract with BioRender

Use the BioRender MCP tools. **BioRender is for converting published papers only.**
Never send unpublished work, internal methods or anything the user has not already
published; draw those locally instead and say so.

1. `custom-figure-create-session` with a `prompt` describing the scene. Write the
   prompt as a numbered left-to-right walkthrough of the pipeline, naming the
   biological objects to draw (cell types and their receptors, droplets, transcripts,
   enzymes, virions, sequencer) and the label text for each. End with a style line:
   flat vector, publication quality, muted colour, generous white space, horizontal
   layout. Describe what is in the paper, not what looks nice.
2. Poll `custom-figure-get-preview-job` with the returned `jobId` until
   `status` is `completed`. It takes roughly 30 to 60 seconds. Stop on `failed` or
   `content_moderation_error` and report the error rather than retrying blindly.
3. `custom-figure-get-session` with the `sessionId`. This returns the preview image
   and finalizes it as a saved BioRender figure.
4. The inline image handed back is a downscaled preview. For print, download the
   full-resolution file from `figure.imageUrl` to `<original_stem>_figure.jpg`
   next to the PDF:

   ```bash
   curl -sS -o "<original_stem>_figure.jpg" "<figure.imageUrl>"
   ```

   That URL is signed and expires in about 30 minutes, so download it in the same
   session, not later. Despite the `.png` in the URL the bytes are usually JPEG;
   name the local file `.jpg`.
5. **Look at the generated image before using it.** It is generated art and can
   invent structures or mislabel them. Check that every object matches the paper:
   right cell types, right molecules, labels spelled correctly, no invented step.
   Regenerate with a corrected prompt if it is wrong, and tell the user what was
   wrong rather than quietly shipping it.

Keep `figure.url` (the BioRender editor link) and report it, so the user can edit
the drawing by hand afterwards.

### 4. Convert to PDF

Invoke the `md_to_pdf` skill on the markdown file. It handles styling and PDF
output automatically, and embeds the figure referenced by the markdown.

### 5. Clean up

After the PDF is confirmed, delete the intermediate `_summary.md` and any
`_summary_diagrams/` cache directory — the PDF is the deliverable. **Keep
`<original_stem>_figure.jpg`**: it is the artwork, it cannot be regenerated
identically, and the signed BioRender URL will have expired.

Then ask: keep locally, or send to tablet?
