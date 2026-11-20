---
name: case_notebooks
description: "Generate and execute the two exploration notebooks for a tumour/normal case after Sarek and the step-3 tiering: (1) SNVs and indels (Mutect2 + Strelka2 tiers, Dog10K, VEP, trace a variant, gene panel) and (2) SVs and copy number (Manta, CNVkit, FACETS purity/ploidy and diploid-vs-doubled refit, driver allelic state, HRD scar, HR genes, MSIsensor-pro). Trigger: user asks for the case notebooks, a step-3 / SV-CNV notebook for a new case, or /case_notebooks."
---

# /case_notebooks

Writes Jupyter notebooks for one case from a JSON config, then executes them. The notebooks only explore and
compute. The interpretation goes in the case's results documents (e.g. `TIERING.md`), or in case-specific extra
cells.

## Usage

```
/case_notebooks <case_dir> [snv|sv_cnv|both]
```

## Inputs

All paths are relative to `case_dir`. `<prefix>` is the pair name (e.g. `ffpe_vs_pbmc`). `<t>` and `<n>` are the
Sarek sample IDs (e.g. `winston_ffpe`, `winston_pbmc`).

**SNV notebook** (required):
- `vep/<prefix>.strelka2_mutect2_fullanno.vep.tsv` is the current step-3 table. It needs the columns TIER, STATUS,
  D10K_*, M2_T_ALT, M2_T_RVAF, S2_T_ALT, GENE_NAME and HUMAN_SYMBOL. Older tables, such as Loulou 2_run, lack
  them, and the notebook stops with the list of missing columns.
- `norm/{mutect2,strelka2,pbmc_germline}.norm.vcf.gz` (+ .tbi). Override the paths with `norm_vcfs`.

**SV/CNV notebook.** Each section is built only when its inputs exist. The script prints what it found and what is
missing:

| Section | Default path | Override key in `paths` |
|---|---|---|
| Manta | `vep/<prefix>.manta_somatic_sv.vep.tsv` | `sv_tsv` |
| Manta germline check | `manta/<t>_vs_<n>/<t>_vs_<n>.manta.diploid_sv.vcf.gz` | `manta_pair` |
| | `manta/<n>/<n>.manta.diploid_sv.vcf.gz` | `manta_normal` |
| CNVkit | `cnvkit/<t>.md.cnr` | `cnr` |
| | `cnvkit/<t>.md.somatic.call.cns` | `cns` |
| CNVkit normal-alone control | `cnvkit/pbmc_only/<n>.md.cns` | `normal_cns` |
| FACETS | `facets/<facets_prefix>.facets.cval<c>.{summary,segments}.tsv`, `.png` | `facets_dir` |
| MSIsensor-pro | `msisensorpro/<t>_vs_<n>` | `msi` |
| Gene copy number, HR copy number | `gene_coords` (config key) | |
| HR germline | `hr_germline_tsv` (config key) | |

Build the gene-coordinate table once per reference with
`scripts/make_gene_coords.py --gtf <ensembl.gtf.gz> --gene-names <gene_names.tsv> --out cnvkit/<ref>.gene_coords.tsv`.

## Steps

1. **Check the inputs** in `case_dir`, against the table above. If the step-3 table is missing, stop and tell the
   user: this skill does not run the step-3 chain.
2. **Write `case_dir/notebooks.json`.** Start from `assets/case.example.json` (Winston). Before filling in sex, the
   driver, the panel or the tumour type, check the case facts in `~/secore-wiki/Cases/<name>/` and
   `CRITICAL_FACTS.md`. Ask the user for anything not on record. The keys:
   - `case`, `case_dir`, `prefix`: required. `tumour_id` and `normal_id` are required for the SV/CNV notebook.
   - `tumour_label`, `normal_label`: text for the titles, e.g. "FFPE tumour" and "PBMC".
   - `sex`: `male` adds the X-chromosome notes.
   - `autosomes`: defaults to dog 1–38. Set it for other species.
   - `driver`: `{gene, chrom, pos, label}`. The SNV notebook traces it. The SV/CNV notebook tests its VAF against
     every allelic state at the locus. Leave it out if the case has no clear driver.
   - `panel`: `{file, title, source}`. `file` is either a name under `assets/panels/` (e.g. `hsa_megquier2019`) or
     a TSV with the columns `gene` and `class`. `source` is the citation text shown in the notebook.
   - `example_genes`: genes looked up in both notebooks.
   - `plot_regions`: a list of `[chrom, start, end]`. Use `null` for the whole chromosome.
   - `facets_prefix`, `facets_cvals`: the first cval is the working fit.
   - `facets_doubtful`: FACETS segments, as `[chrom, start, end]`, whose EM state disagrees with their allelic
     imbalance. Fill this in after the first run, then regenerate.
   - `support_rule`: must match the step-3 run (default 5 alt reads, VAF 5%).
   - `docs`: the case's methods document, referenced in the notebooks.
   - `extra_cells`: `{"snv": "<file>.py", "sv_cnv": "<file>.py"}`. Each is a Python file that defines `cells`, a
     list built with the given `md()` and `code()`, which is appended to that notebook. Put case-specific notes
     here, such as manual SV assessments or conclusions, never in the generator.
3. **Generate and execute.** You need a Python with nbformat, nbconvert, ipykernel, pandas, matplotlib, scipy and
   pysam. On the SeCore server the `secore` conda env has them all. On another machine, activate the plugin's
   `science` env (`source <skill>/../../scripts/ensure_env.sh`). If it lacks them, install them into it once with
   `conda install -n science -c conda-forge -c bioconda nbformat nbconvert ipykernel pandas matplotlib scipy pysam`.
   ```
   PY=/home/fab/miniforge3/envs/secore/bin/python   # or: PY=python, inside the science env
   $PY <skill>/scripts/make_snv_notebook.py    <case_dir>/notebooks.json
   $PY <skill>/scripts/make_sv_cnv_notebook.py <case_dir>/notebooks.json
   cd <case_dir> && $PY -m nbconvert --to notebook --execute --inplace <prefix>_step3.ipynb <prefix>_sv_cnv_facets_msi_hrd.ipynb
   ```
   Both run in about a minute on an exome. Use `--out` to write the notebooks somewhere else.
4. **Check for errors and report.** Scan the executed notebooks for error outputs. Report the final Summary table
   of the SV/CNV notebook: purity and ploidy, the refit, the driver state, HRD and MSI. Flag where the
   diploid-vs-doubled refit disagrees with the FACETS ploidy.

## What the numbers are and are not

- The refit scans purity for a diploid (1:1) and a doubled (2:2) baseline and scores integer states on both log
  ratio and allelic imbalance. It is a model comparison, not a replacement for FACETS.
- HRD-LOH and LST are FACETS-based approximations. TAI is not computed. The threshold of 42 and the MSI cut-off of
  3.5% are human: say so whenever you quote them.
- Do not write therapy conclusions from these notebooks. They belong in the results document, as research only.
