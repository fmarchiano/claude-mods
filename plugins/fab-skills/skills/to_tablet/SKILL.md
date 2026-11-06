---
name: to_tablet
description: "Copy one or more existing PDF files to the Galaxy tablet (Termux sshd over Tailscale) into a folder under Documents chosen by the user, with a media scan so they show in Android's file browser. Trigger: user asks to copy/send/push a PDF to the tablet, or /to_tablet."
---

# /to_tablet

Copy existing PDF file(s) to the tablet. Does not convert anything; use
`/md_to_pdf` first if the source is Markdown.

## Usage

```
/to_tablet <file1.pdf> [file2.pdf ...]
```

## What it does

Runs `scripts/push.sh`, which for each PDF:
1. Appends the creation date and hour to the name as `_YYYY-MM-DD_HHMM` (taken
   from the file's modification time), unless the name already ends with one.
   `report.pdf` is sent as `report_2026-10-21_1430.pdf`.
2. `scp` it into each chosen folder under `/storage/emulated/0/Documents/`.
3. Triggers the Android media scanner for that file.

No local copy is made; the source file is left untouched.

### Choosing the destination folder (required before copying)

Before running the script, Claude must:
1. List the folders in Documents:
   `ssh -p 8022 u0_a134@100.94.60.70 'ls -d /storage/emulated/0/Documents/*/'`
2. Ask the user with AskUserQuestion (multiSelect: true) which Documents folder(s)
   to copy to, with one option per folder found. AskUserQuestion takes at most 4
   options: if there are more, offer the most likely ones (by the PDF's topic)
   and let the user type any other name through "Other".
3. If a chosen folder has subfolders (`ls -d <folder>/*/`), ask once more which
   subfolder(s), with "<folder> itself" as one option.
4. Run the script with `TABLET_SUBDIRS` set to the chosen paths relative to
   Documents, space-separated (e.g. `TABLET_SUBDIRS="allovista Secore/Canine"`).
   Leave it empty for Documents itself.

Multiple selections copy the same PDF into each folder. A folder name the user
types that does not exist yet is created.

### After the copy: settle the open decisions (required when the PDF has a Markdown source)

The user reads the PDF on the tablet while Claude works through the document's
open choices with them. Once the copy is done, Claude must:

1. Re-read the source Markdown (the `.md` next to the PDF) and list every open decision in it: open
   questions, `[Open]` tags, unresolved gaps, "to confirm" or "TBD" items,
   parameter values not yet fixed, and recommendations still waiting for sign-off.
2. Ask them with AskUserQuestion, up to 4 questions per call, as many calls as
   needed until none are left. Two kinds of question:
   - **Parameter choice** (e.g. a threshold, bin size, tool version): 2 to 4
     concrete values. Put the recommended one first, mark it "(Recommended)",
     and give a one-line trade-off for each.
   - **Direction question** (scope, cohort, design approach, what to build next):
     2 to 4 distinct paths, each with what it commits us to. The user can type a
     free answer through "Other" for anything not listed.
   Use the section name or gap ID (e.g. "G6") in the `header` so the user can
   find it in the PDF. Make each question stand alone, because the user may not
   be on that page.
3. Write the answers back into the Markdown (mark the item decided, with the
   choice and date), regenerate the PDF with `md_to_pdf` (`convert.sh`) and push it again to the same tablet folder(s).
4. End with a short list of the next moves that follow from the decisions.

If the document has no open decisions, say so in one line and skip the questions.

## Invocation

```bash
TABLET_SUBDIRS="allovista Secore/Canine" bash <this skill's base directory>/scripts/push.sh <file1.pdf> [file2.pdf ...]
```

Override `TABLET_HOST`, `TABLET_PORT` or `TABLET_DIR` via env if the tablet address changes.
