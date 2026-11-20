"""Shared by make_snv_notebook.py and make_sv_cnv_notebook.py: read the case config, resolve paths, write the notebook."""
import json
import runpy
import sys
from pathlib import Path

import nbformat as nbf

SKILL_DIR = Path(__file__).resolve().parent.parent
md_cell, code_cell = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

DEFAULTS = {
    "tumour_label": "tumour",
    "normal_label": "normal",
    "sex": "unknown",
    "autosomes": [str(i) for i in range(1, 39)],  # dog; set for other species
    "norm_vcfs": {"mutect2": "norm/mutect2.norm.vcf.gz", "strelka2": "norm/strelka2.norm.vcf.gz",
                  "germline": "norm/pbmc_germline.norm.vcf.gz"},
    "support_rule": {"min_alt": 5, "min_vaf": 0.05},
    "panel": None,
    "example_genes": [],
    "driver": None,
    "facets_prefix": "tumour",
    "facets_cvals": [150, 300],
    "facets_doubtful": [],
    "plot_regions": [],
    "gene_coords": "cnvkit/gene_coords.tsv",
    "hr_germline_tsv": "hr_genes/pbmc_hr.vep.tsv",
    "docs": "TIERING.md",
    "extra_cells": {},
}


def load_config(argv=None):
    """Read the case JSON named on the command line and fill in the defaults."""
    import argparse
    parser = argparse.ArgumentParser(description=sys.modules["__main__"].__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("config", help="case JSON (see assets/case.example.json)")
    parser.add_argument("--out", help="notebook path (default: in case_dir, named from prefix)")
    args = parser.parse_args(argv)
    cfg = {**DEFAULTS, **json.loads(Path(args.config).read_text())}
    for key in ("case", "case_dir", "prefix"):
        if key not in cfg:
            parser.error(f"{args.config}: '{key}' is required")
    cfg["case_dir"] = str(Path(cfg["case_dir"]).expanduser().resolve())
    cfg["autosomes"] = [str(c) for c in cfg["autosomes"]]
    return cfg, args.out


def case_path(cfg, rel):
    return Path(cfg["case_dir"]) / rel


def panel_genes(cfg):
    """(gene -> class dict, title, source text) for the configured panel, or None.
    panel.file is a name under assets/panels/ (without .tsv) or a path to a TSV with columns gene, class."""
    panel = cfg.get("panel")
    if not panel:
        return None
    f = Path(panel["file"])
    if not f.suffix:
        f = SKILL_DIR / "assets" / "panels" / f"{panel['file']}.tsv"
    elif not f.is_absolute():
        f = case_path(cfg, f)
    rows = [line.split("\t") for line in f.read_text().splitlines()[1:] if line.strip()]
    return ({g: c for g, c in rows}, panel.get("title", "Panel genes"), panel.get("source", ""))


def hr_genes():
    return (SKILL_DIR / "assets" / "hr_genes.tsv").read_text().split()[1:]


def fill(text, cfg):
    """Replace {CASE}, {TUMOUR}, {NORMAL}, {PREFIX} and {DOCS} in markdown."""
    for token, key in (("{CASE}", "case"), ("{TUMOUR}", "tumour_label"), ("{NORMAL}", "normal_label"),
                       ("{PREFIX}", "prefix"), ("{DOCS}", "docs")):
        text = text.replace(token, str(cfg[key]))
    return text


def write(cells, cfg, out, default_name, extra_key):
    """Append the case's extra cells (a .py defining `cells`, given md and code), then write the notebook."""
    extra = cfg["extra_cells"].get(extra_key)
    if extra:
        ns = runpy.run_path(str(case_path(cfg, extra)), init_globals={"md": md_cell, "code": code_cell})
        cells = cells + ns["cells"]
    nb = nbf.v4.new_notebook(cells=cells)
    nb.metadata["kernelspec"] = {"display_name": "Python 3 (ipykernel)", "language": "python", "name": "python3"}
    out = Path(out) if out else case_path(cfg, default_name)
    nbf.write(nb, out)
    print(f"wrote {out} ({len(cells)} cells)")
