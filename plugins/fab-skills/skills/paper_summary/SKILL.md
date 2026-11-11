---
name: paper-summary
description: "Summarize a scientific paper PDF into a graphical abstract PDF: citation header, synthesized background, Mermaid methods flow diagram, key finding. Runs in the `science` conda env, created automatically if missing. Trigger: summarize paper, paper summary, graphical abstract, summarize this PDF, paper overview."
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
Target these sections only — skip detailed results and references:

- **First 3 pages**: title, authors, journal, DOI, abstract, start of introduction.
- **Introduction** (remaining pages if it continues).
- **Methods / Materials and Methods**: read fully — this is the core output.
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

<Single synthesized paragraph. Open with the problem and gap the paper addresses
(from introduction). Close with what the authors found or concluded (from
discussion/conclusion). 4–8 sentences. No jargon the abstract doesn't use.>

## Methods

` ` `mermaid
flowchart LR
    A["<Sample / input material>"] --> B["<Library prep technique>"]
    B --> C["<Sequencing platform & mode>"]
    C --> D["<Primary bioinformatics pipeline>"]
    D --> E["<Key downstream analysis>"]
` ` `

<One sentence per node explaining the specific technique, kit, or tool used.
Use a definition list:>

**<Node A label>**
: <detail>

**<Node B label>**
: <detail>

**<Node C label>**
: <detail>

**<Node D label>**
: <detail>

**<Node E label>**
: <detail>

::: callout
**Key Finding.** <One sentence: the single most important result or conclusion.>
:::
```

Adapt the Mermaid node count to the actual pipeline — more nodes if the paper
has more wet-lab or bioinformatics stages, fewer if it's simpler. The five-node
template is a starting shape, not a constraint.

Completion: the markdown file exists, renders valid Mermaid, and uses md_to_pdf
frontmatter.

### 3. Convert to PDF

Invoke the `md_to_pdf` skill on the markdown file. It handles Mermaid rendering,
styling, and PDF output automatically.

### 4. Clean up

After the PDF is confirmed, delete the intermediate `_summary.md` and any
`_summary_diagrams/` cache directory — the PDF is the deliverable.

Then ask: keep locally, or send to tablet?
