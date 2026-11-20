"""Write <prefix>_step3.ipynb, the exploration notebook for a tumour/normal step-3 table (Mutect2 + Strelka2
union, tiers, Dog10K, VEP, gene names).

Input: <case_dir>/vep/<prefix>.strelka2_mutect2_fullanno.vep.tsv and the normalised caller VCFs (norm_vcfs).
Usage: python make_snv_notebook.py case.json [--out notebook.ipynb]
Then:  jupyter nbconvert --to notebook --execute --inplace <notebook>
"""
from common import case_path, code_cell, fill, load_config, md_cell, panel_genes, write

cfg, out = load_config()
code = code_cell
fullanno = case_path(cfg, f"vep/{cfg['prefix']}.strelka2_mutect2_fullanno.vep.tsv")
if not fullanno.exists():
    raise SystemExit(f"missing {fullanno}: run the step-3 chain and VEP first")
panel = panel_genes(cfg)
norm = {k: str(case_path(cfg, v)) for k, v in cfg["norm_vcfs"].items()}
rule = cfg["support_rule"]
md = lambda s: md_cell(fill(s, cfg).replace("{MIN_ALT}", str(rule["min_alt"]))
                       .replace("{MIN_VAF}", f"{100 * rule['min_vaf']:g}%"))

cells = [
md("""# {CASE}: {TUMOUR} vs {NORMAL}, step 3 (Mutect2 + Strelka2, tiers, VEP)

Explore the tiered calls and trace any variant through both callers. Method and rationale: `{DOCS}`.

- `vep/{PREFIX}.strelka2_mutect2_fullanno.vep.tsv`: every candidate from either caller (one row per allele),
  with FILTER reasons per caller, read metrics, Dog10K fields and the VEP picked transcript (canonical first):
  `SYMBOL`, `Gene`, `Consequence`, `IMPACT`, `HGVSc`, `HGVSp`, ...
- `step3/{PREFIX}.step3.<tier>.vcf.gz`, `vep/*.vep.vcf.gz`: one sites-only VCF per tier, plain and annotated.
- `norm/*.norm.vcf.gz`: the normalised raw caller VCFs, for the full INFO/FORMAT of any record.

**TIER** (support rule: >= {MIN_ALT} tumour alt reads and read VAF >= {MIN_VAF}; for consensus calls, in each caller):

| Tier | Meaning |
|---|---|
| `HIGH_CONF_BOTH_PASS` | both callers PASS (exact match) and both meet the support rule |
| `BOTH_PASS` | both callers PASS, support rule missed; still likely true |
| `HIGH_CONF_BOTH_PASS_NEAR` / `BOTH_PASS_NEAR` | the same for near-matched indels |
| `HIGH_CONF_SINGLE_CALLER` | one caller PASS, meets the support rule |
| `LOW_CONF_SINGLE_CALLER` | one caller PASS, support rule missed |
| `NO_PASS` | neither caller PASS |

`STATUS` says which caller passed (`BOTH_PASS`, `BOTH_PASS_NEAR`, `MUTECT2_PASS`, `STRELKA2_PASS`, `NO_PASS`).
`M2_FILTER` / `S2_FILTER` list why a record failed in that caller (`|`-separated), or `not_called`.

**Step-2 normal reasons** (both callers): `pbmc_germline` (PASS germline call in the normal's Strelka2 at that
position), `normal_lowcov` (normal depth < 15), `normal_2alt_reads` (>= 2 alt reads in the normal).

**Dog10K** is annotation only: `D10K_AF`, `D10K_AN`, `D10K_FILTER`, `D10K_KNOWN` (AF >= 0.001).

**Gene names**: `GENE_NAME` fills the gaps of the reference annotation from dog and human orthologues
(`NAME_SOURCE` says how); `HUMAN_SYMBOL` is the human orthologue."""),
code(f"""from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pysam

pd.set_option("display.max_columns", None)
pd.set_option("display.max_colwidth", 60)

CASE_DIR = Path({cfg['case_dir']!r})
FULLANNO_TSV = CASE_DIR / {f"vep/{cfg['prefix']}.strelka2_mutect2_fullanno.vep.tsv"!r}
M2_NORM = Path({norm['mutect2']!r})
S2_NORM = Path({norm['strelka2']!r})
GERMLINE_NORM = Path({norm['germline']!r})

TIERS = ["HIGH_CONF_BOTH_PASS", "BOTH_PASS", "HIGH_CONF_BOTH_PASS_NEAR", "BOTH_PASS_NEAR",
         "HIGH_CONF_SINGLE_CALLER", "LOW_CONF_SINGLE_CALLER", "NO_PASS"]
PASS_TIERS = [t for t in TIERS if t != "NO_PASS"]
# Fixed categorical order (validated: CVD and normal-vision separation pass; tables and legends carry the labels)
TIER_COLOUR = {{"HIGH_CONF_BOTH_PASS": "#2a78d6", "BOTH_PASS": "#eb6834",
               "HIGH_CONF_SINGLE_CALLER": "#1baf7a", "LOW_CONF_SINGLE_CALLER": "#eda100"}}
MIN_ALT, MIN_VAF = {rule['min_alt']}, {rule['min_vaf']}"""),
md("## Load"),
code("""full = pd.read_csv(FULLANNO_TSV, sep="\\t", dtype={"chrom": str, "EXON": str, "INTRON": str}, low_memory=False)
NEEDED = ["TIER", "STATUS", "CALLED_BY", "MATCH", "TYPE", "M2_FILTER", "S2_FILTER", "M2_T_ALT", "M2_T_RVAF", "M2_N_DP",
          "S2_T_ALT", "S2_T_VAF", "S2_N_DP", "D10K_AF", "D10K_KNOWN", "GENE_NAME", "HUMAN_SYMBOL"]
missing = [c for c in NEEDED if c not in full.columns]
assert not missing, f"older step-3 table, columns missing: {missing}"
TEXT_COLS = [c for c in ["M2_FILTER", "S2_FILTER", "S2_REPR", "D10K_FILTER", "SYMBOL", "Gene", "Consequence", "IMPACT",
             "BIOTYPE", "Feature", "CANONICAL", "EXON", "INTRON", "HGVSc", "HGVSp", "Protein_position", "Amino_acids",
             "DOMAINS", "GENE_NAME", "NAME_SOURCE", "HUMAN_SYMBOL"] if c in full.columns]
full[TEXT_COLS] = full[TEXT_COLS].fillna("")
full["D10K_KNOWN"] = full["D10K_KNOWN"].astype(bool)
# Gene label: GENE_NAME where there is one, else the Ensembl gene ID
full["GENE"] = full["GENE_NAME"].where(full["GENE_NAME"] != "", full["Gene"])

# Tumour support from the caller that decides the tier: Mutect2 for consensus and Mutect2-only calls,
# Strelka2 for Strelka2-only calls (and for NO_PASS rows Strelka2 did not see, Mutect2)
use_m2 = full["STATUS"].isin(["BOTH_PASS", "BOTH_PASS_NEAR", "MUTECT2_PASS"]) | (
    (full["STATUS"] == "NO_PASS") & full["M2_T_ALT"].notna())
full["T_ALT"] = full["M2_T_ALT"].where(use_m2, full["S2_T_ALT"])
full["T_VAF"] = full["M2_T_RVAF"].where(use_m2, full["S2_T_VAF"])
full["T_DEPTH"] = (full["T_ALT"] / full["T_VAF"]).round()  # ref + alt reads
full["N_DP"] = full["M2_N_DP"].where(use_m2, full["S2_N_DP"])
SNV = full["TYPE"] == "SNV"
full["SUBST"] = ""
comp = str.maketrans("ACGT", "TGCA")
ref_pyr = full["ref"].isin(["C", "T"])
full.loc[SNV, "SUBST"] = np.where(ref_pyr[SNV], full.loc[SNV, "ref"] + ">" + full.loc[SNV, "alt"],
                                  full.loc[SNV, "ref"].str.translate(comp) + ">" + full.loc[SNV, "alt"].str.translate(comp))
passed = full[full["TIER"] != "NO_PASS"].copy()
print(full.shape, "candidates;", len(passed), "in a PASS tier")
full.head()"""),
md("## Overview"),
code("""pd.crosstab(full["TIER"], full["TYPE"], margins=True).reindex(TIERS + ["All"]).dropna(how="all")"""),
code("""# Known Dog10K variants (AF >= 0.001) per tier and type: high shares point to germline leakage
known = pd.crosstab([passed["TIER"], passed["TYPE"]], passed["D10K_KNOWN"], margins=True)
known["% known"] = (100 * known.get(True, 0) / known["All"]).round(0)
known"""),
code("""pd.crosstab(full["STATUS"], full["TYPE"], margins=True)"""),
code("""pd.crosstab(full["CALLED_BY"], full["MATCH"], margins=True)"""),
md("""### Step-2 normal rules

Records the caller itself passed, and what the normal-sample rules did to them (a record can fail more than one
rule)."""),
code("""STEP2 = {"pbmc_germline", "normal_lowcov", "normal_2alt_reads"}
def step2_table(col):
    f = full[col]
    caller_pass = f.map(lambda x: x not in ("", "not_called") and set(x.split("|")) <= STEP2 | {"PASS"})
    sub = f[caller_pass]
    counts = {r: int(sub.str.contains(r).sum()) for r in sorted(STEP2)}
    counts["caller PASS"] = int(caller_pass.sum())
    counts["final PASS"] = int((f == "PASS").sum())
    return pd.Series(counts)

pd.DataFrame({"Mutect2": step2_table("M2_FILTER"), "Strelka2": step2_table("S2_FILTER")})"""),
md("""## Read support per tier

Tumour VAF against tumour depth (ref + alt reads), one panel per tier, on log axes. The dashed lines mark the
support rule: VAF = {MIN_VAF} and alt reads = {MIN_ALT} (the diagonal VAF = {MIN_ALT} / depth). High-confidence calls sit
above both. Hollow markers are known Dog10K variants. Calls with exactly k alt reads lie on a diagonal streak."""),
code("""fig, axes = plt.subplots(1, 4, figsize=(16, 4.2), sharex=True, sharey=True)
depth = np.logspace(0.5, 3.7, 50)
for ax, tier in zip(axes, TIER_COLOUR):
    d = passed[passed["TIER"] == tier]
    c = TIER_COLOUR[tier]
    for kn, face in [(False, c), (True, "none")]:
        x = d[d["D10K_KNOWN"] == kn]
        ax.scatter(x["T_DEPTH"], x["T_VAF"], s=10, facecolors=face, edgecolors=c, linewidths=0.8,
                   label="known in Dog10K" if kn else "not in Dog10K")
    ax.axhline(MIN_VAF, color="0.4", ls="--", lw=0.8)
    ax.plot(depth, np.minimum(MIN_ALT / depth, 1), color="0.4", ls="--", lw=0.8)
    ax.set(xscale="log", yscale="log", title=f"{tier}\\n(n={len(d)})", xlabel="tumour depth (reads)")
    ax.set_ylim(0.003, 1.05)
    ax.grid(color="0.92", lw=0.6)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylabel("tumour read VAF")
axes[0].legend(frameon=False, fontsize=8, loc="lower left")
plt.tight_layout()"""),
code("""# Substitution spectrum per tier (SNVs, pyrimidine reference). FFPE damage inflates C>T in weakly supported calls.
spec = pd.crosstab(passed.loc[passed["TYPE"] == "SNV", "TIER"], passed.loc[passed["TYPE"] == "SNV", "SUBST"],
                   normalize="index").mul(100).round(1)
spec.reindex([t for t in TIERS if t in spec.index])"""),
md("## Consensus calls (HIGH_CONF_BOTH_PASS and BOTH_PASS)"),
code("""both = passed[passed["STATUS"].isin(["BOTH_PASS", "BOTH_PASS_NEAR"])].copy()
pd.crosstab([both["TIER"], both["IMPACT"].replace("", "none")], both["TYPE"], margins=True)"""),
code("""# Protein-changing consensus calls (HIGH / MODERATE impact)
COLS = ["TIER", "chrom", "pos", "ref", "alt", "GENE", "HUMAN_SYMBOL", "Consequence", "IMPACT", "HGVSp", "DOMAINS",
        "T_VAF", "T_ALT", "T_DEPTH", "N_DP", "D10K_AF"]
coding = both[both["IMPACT"].isin(["HIGH", "MODERATE"])]
coding[COLS].sort_values(["TIER", "IMPACT", "T_VAF"], ascending=[False, True, False])"""),
code("""cols = ["TIER", "chrom", "pos", "ref", "alt", "TYPE", "GENE", "Consequence", "HGVSp",
        "M2_T_RVAF", "S2_T_VAF", "M2_T_ALT", "S2_T_ALT", "M2_T_DP", "S2_T_DP", "M2_N_DP", "M2_N_ALT", "S2_N_ALT",
        "M2_TLOD", "S2_EVS", "D10K_AF"]
both[[c for c in cols if c in both.columns]].sort_values("M2_T_RVAF", ascending=False)"""),
code("""both.groupby("TIER")[["M2_T_RVAF", "S2_T_VAF", "M2_T_ALT", "M2_T_DP", "M2_N_DP", "M2_TLOD", "S2_EVS"]].describe().T.round(3)"""),
code("""fig, axes = plt.subplots(1, 2, figsize=(11, 4))
bins = np.linspace(0, 0.6, 41)
for tier in ["HIGH_CONF_BOTH_PASS", "BOTH_PASS"]:
    d = both[both["TIER"] == tier]
    axes[0].hist(d["M2_T_RVAF"], bins=bins, color=TIER_COLOUR[tier], alpha=0.8, label=f"{tier} (n={len(d)})",
                 edgecolor="white", linewidth=0.5)
    axes[1].scatter(d["M2_T_RVAF"], d["S2_T_VAF"], s=12, color=TIER_COLOUR[tier], label=tier)
axes[0].axvline(MIN_VAF, color="0.4", ls="--", lw=0.8)
axes[0].set(xlabel="tumour read VAF (Mutect2)", ylabel="sites", title="Consensus VAF")
axes[1].plot([0, 1], [0, 1], lw=0.8, color="0.6")
axes[1].set(xlabel="Mutect2 read VAF", ylabel="Strelka2 VAF", title="Caller agreement")
for ax in axes:
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()"""),
md("""The VAF of a clonal heterozygous SNV in a copy-neutral region is tumour fraction / 2 in a diploid tumour. Read
VAF peaks as purity only together with the copy-number fit (SV/CNV notebook)."""),
code("""# Consensus calls per chromosome
both["chrom"].value_counts().sort_index(key=lambda s: s.map(lambda c: (not c.isdigit(), int(c) if c.isdigit() else 0, c)))"""),
md("""## Single-caller calls

`HIGH_CONF_SINGLE_CALLER` meets the support rule in the caller that passed it. Where its indels are mostly known
Dog10K sites (see the overview), treat them as possible germline leakage until checked in the normal."""),
code("""single_hi = passed[passed["TIER"] == "HIGH_CONF_SINGLE_CALLER"]
pd.crosstab([single_hi["STATUS"], single_hi["IMPACT"].replace("", "none")], single_hi["TYPE"], margins=True)"""),
code("""single_hi[single_hi["IMPACT"].isin(["HIGH", "MODERATE"])][["STATUS"] + COLS].sort_values(["D10K_AF", "T_VAF"], ascending=[True, False], na_position="first")"""),
code("""# HIGH-impact low-confidence calls, the best supported first
single_lo = passed[passed["TIER"] == "LOW_CONF_SINGLE_CALLER"]
single_lo[single_lo["IMPACT"] == "HIGH"][["STATUS"] + COLS].sort_values("T_ALT", ascending=False).head(30)"""),
md("""### Why single-caller PASS variants dropped out

For variants that PASS in one caller, what did the other caller say?"""),
code("""from IPython.display import display

def reason_counts(df, col):
    return (df[col].str.split("|").explode().replace("", "PASS")
            .value_counts().rename_axis("reason").to_frame("variants"))

m2_only = full[full["STATUS"] == "MUTECT2_PASS"]
s2_only = full[full["STATUS"] == "STRELKA2_PASS"]
print(f"MUTECT2_PASS: {len(m2_only)}  -> Strelka2 reasons")
display(reason_counts(m2_only, "S2_FILTER"))
print(f"STRELKA2_PASS: {len(s2_only)}  -> Mutect2 reasons")
display(reason_counts(s2_only, "M2_FILTER"))"""),
code("""# Variants failing only on the step-2 normal rules in the other caller (closest to consensus)
def only_step2(f):
    return f not in ("", "not_called") and set(f.split("|")) <= STEP2

near_miss = pd.concat([m2_only[m2_only["S2_FILTER"].map(only_step2)],
                       s2_only[s2_only["M2_FILTER"].map(only_step2)]])
print(len(near_miss))
near_miss[["TIER", "STATUS", "chrom", "pos", "ref", "alt", "GENE", "M2_FILTER", "S2_FILTER", "Consequence",
           "T_VAF", "T_ALT", "M2_N_DP", "S2_N_DP", "M2_N_ALT", "S2_N_ALT"]].head(30)"""),
md("""## Trace a variant

`trace("chrom", pos)` lists every row of the full annotation within `window` bp, so an indel that the two callers
placed differently also shows up. `raw("chrom", pos)` prints the original normalised Mutect2, Strelka2 and normal
germline records with all INFO/FORMAT fields. `gene(name)` lists all candidates in a gene (dog name, human symbol or
Ensembl gene ID). `trace_region("chrom:start-end")` lists every candidate in a region."""),
code("""def trace(chrom, pos, window=10):
    chrom = str(chrom)
    hits = full[(full["chrom"] == chrom) & full["pos"].between(pos - window, pos + window)]
    if hits.empty:
        print(f"{chrom}:{pos} ±{window}: not called by Mutect2 or Strelka2")
    return hits

def raw(chrom, pos, window=0):
    for label, path in [("Mutect2", M2_NORM), ("Strelka2", S2_NORM), ("normal germline", GERMLINE_NORM)]:
        with pysam.VariantFile(str(path)) as vcf:
            recs = list(vcf.fetch(str(chrom), max(0, pos - 1 - window), pos + window))
        print(f"=== {label}: {len(recs)} record(s)")
        for rec in recs:
            print(str(rec).rstrip())

def trace_region(region):
    chrom, span = region.split(":")
    start, end = (int(x.replace(",", "")) for x in span.split("-"))
    return full[(full["chrom"] == chrom) & full["pos"].between(start, end)]

def gene(name):
    hit = (full["GENE_NAME"] == name) | (full["HUMAN_SYMBOL"] == name) | (full["Gene"] == name)
    return full[hit][["chrom", "pos", "ref", "alt", "GENE", "TIER", "STATUS", "CALLED_BY", "M2_FILTER", "S2_FILTER",
                      "Consequence", "HGVSp", "T_VAF", "T_ALT", "T_DEPTH", "M2_N_DP", "M2_N_ALT", "S2_N_ALT", "D10K_AF"]]"""),
]

driver = cfg.get("driver")
if driver:
    cells += [md(f"**Example: {driver['label']} ({driver['chrom']}:{driver['pos']:,}).**"),
              code(f"""gene({driver['gene']!r})"""),
              code(f"""raw({str(driver['chrom'])!r}, {driver['pos']})""")]
cells += [code(f"""gene({g!r})""") for g in cfg["example_genes"] if not driver or g != driver["gene"]]

if panel:
    genes, title, source = panel
    cells += [
        md(f"""## {title}

{source}

All PASS-tier calls in these genes, matched on the human orthologue or the dog gene name. Copy-number genes are
listed for SNVs and indels only; copy number is in the SV/CNV notebook."""),
        code(f"""PANEL = {genes!r}
in_panel = full["HUMAN_SYMBOL"].isin(PANEL) | full["GENE_NAME"].isin(PANEL)
panel = passed[in_panel.loc[passed.index]].copy()
panel["panel"] = panel["HUMAN_SYMBOL"].where(panel["HUMAN_SYMBOL"].isin(PANEL), panel["GENE_NAME"]).map(PANEL)
panel[["panel", "chrom", "pos", "ref", "alt", "GENE", "HUMAN_SYMBOL", "TIER", "TYPE", "Consequence", "IMPACT", "HGVSp",
       "T_VAF", "T_ALT", "N_DP", "D10K_AF"]].sort_values(["TIER", "IMPACT", "GENE"])"""),
        code("""# Every coding candidate in the panel genes, any tier, to see what was filtered and why
full[in_panel & full["IMPACT"].isin(["HIGH", "MODERATE"])][
    ["chrom", "pos", "ref", "alt", "GENE", "TIER", "M2_FILTER", "S2_FILTER", "Consequence", "HGVSp", "T_VAF", "T_ALT",
     "D10K_AF"]].sort_values("GENE")"""),
    ]

cells.append(code("""# Search by tier / reason, e.g. Mutect2-only calls lost to low normal coverage in Strelka2
full[(full["STATUS"] == "MUTECT2_PASS") & full["S2_FILTER"].str.contains("normal_lowcov")].head()"""))

write(cells, cfg, out, f"{cfg['prefix']}_step3.ipynb", "snv")
