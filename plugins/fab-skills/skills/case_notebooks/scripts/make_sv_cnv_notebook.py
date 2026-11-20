"""Write <prefix>_sv_cnv_facets_msi_hrd.ipynb, the exploration notebook for a tumour/normal pair's structural
variants (Manta), copy number (CNVkit, FACETS), purity and ploidy, a driver's allelic state, HR deficiency and MSI.

Each section is included only when its inputs exist (default paths below, overridable in the config's `paths`):
  sv_tsv        vep/<prefix>.manta_somatic_sv.vep.tsv            (Manta somatic SVs, VEP-annotated, one row per record)
  manta_pair    manta/<t>_vs_<n>/<t>_vs_<n>.manta.diploid_sv.vcf.gz
  manta_normal  manta/<n>/<n>.manta.diploid_sv.vcf.gz
  cnr, cns      cnvkit/<t>.md.cnr, cnvkit/<t>.md.somatic.call.cns (Sarek variant_calling/cnvkit/)
  normal_cns    cnvkit/pbmc_only/<n>.md.cns                      (normal segmented alone; optional control)
  facets_dir    facets/ with <facets_prefix>.facets.cval<c>.{summary,segments}.tsv and .png
  msi           msisensorpro/<t>_vs_<n>                          (Sarek variant_calling/msisensorpro/)
  snv_tsv       vep/<prefix>.strelka2_mutect2_fullanno.vep.tsv   (step-3 table)
  gene_coords, hr_germline_tsv from the config.
<t> and <n> are tumour_id and normal_id. Usage: python make_sv_cnv_notebook.py case.json [--out notebook.ipynb]
Then:  jupyter nbconvert --to notebook --execute --inplace <notebook>
"""
from common import case_path, code_cell, fill, hr_genes, load_config, md_cell, panel_genes, write

cfg, out = load_config()
md = lambda s: md_cell(fill(s, cfg))
code = code_cell
for key in ("tumour_id", "normal_id"):
    if key not in cfg:
        raise SystemExit(f"config: '{key}' is required (the Sarek sample IDs, e.g. winston_ffpe)")
t, n, fp, prefix = cfg["tumour_id"], cfg["normal_id"], cfg["facets_prefix"], cfg["prefix"]
paths = {"sv_tsv": f"vep/{prefix}.manta_somatic_sv.vep.tsv",
         "manta_pair": f"manta/{t}_vs_{n}/{t}_vs_{n}.manta.diploid_sv.vcf.gz",
         "manta_normal": f"manta/{n}/{n}.manta.diploid_sv.vcf.gz",
         "cnr": f"cnvkit/{t}.md.cnr", "cns": f"cnvkit/{t}.md.somatic.call.cns", "normal_cns": f"cnvkit/pbmc_only/{n}.md.cns",
         "facets_dir": "facets", "msi": f"msisensorpro/{t}_vs_{n}",
         "snv_tsv": f"vep/{prefix}.strelka2_mutect2_fullanno.vep.tsv",
         "gene_coords": cfg["gene_coords"], "hr_germline_tsv": cfg["hr_germline_tsv"], **cfg.get("paths", {})}
P = {k: case_path(cfg, v) for k, v in paths.items()}
cval = cfg["facets_cvals"][0]
has = {"manta": P["sv_tsv"].exists(), "manta_vcfs": P["manta_pair"].exists() and P["manta_normal"].exists(),
       "cnv": P["cnr"].exists() and P["cns"].exists(), "normal_cns": P["normal_cns"].exists(),
       "facets": (P["facets_dir"] / f"{fp}.facets.cval{cval}.segments.tsv").exists(), "msi": P["msi"].exists(),
       "snv": P["snv_tsv"].exists(), "coords": P["gene_coords"].exists(), "hr_germline": P["hr_germline_tsv"].exists()}
print("inputs found:", ", ".join(k for k, v in has.items() if v) or "none")
print("missing:", ", ".join(k for k, v in has.items() if not v) or "none")
if not (has["manta"] or has["cnv"] or has["facets"]):
    raise SystemExit("no Manta, CNVkit or FACETS input found: nothing to build")
driver, panel = cfg.get("driver"), panel_genes(cfg)
male = cfg["sex"] == "male"
look_genes = list(dict.fromkeys(([driver["gene"]] if driver else []) + cfg["example_genes"]))

inputs = []
if has["manta"]:
    inputs.append(f"""**Manta** (`{paths['sv_tsv']}`): one row per somatic SV record, annotated with VEP.
- A translocation is two BND records, which point to each other through `MATE_CHROM` and `MATE_POS`.
- `PR` = spanning read pairs, `SR` = split reads, each as ref,alt. `T_ALT_FRAC` is a rough allele fraction.
- `GENES` lists every gene VEP reports, including genes up to 5 kb up- or downstream. `CODING_GENES` lists only those
  with a HIGH or MODERATE consequence.
- Exome capture means Manta only sees breakpoints in or near captured exons.""")
if has["cnv"]:
    inputs.append(f"""**CNVkit** (paired: the normal is the reference):
- `{paths['cnr']}`: bin-level log2 ratios, for target bins and off-target bins (`Antitarget`).
- `{paths['cns']}`: the segments, with CNVkit's integer copy-number call `cn`.""" + (f"""
- `{paths['normal_cns']}`: the normal segmented on its own, as a control for capture artefacts.""" if has["normal_cns"] else "") + """

log2 = 0 is two copies. With 100% tumour, one copy lost is log2 -1 and one gained is +0.58. Lower purity shrinks
both towards 0.""")
if has["facets"]:
    inputs.append(f"**FACETS** (`{paths['facets_dir']}/`): purity, ploidy and allele-specific copy number, cval "
                  + " and ".join(map(str, cfg["facets_cvals"])) + ".")
if has["msi"]:
    inputs.append(f"**MSIsensor-pro** (`{paths['msi']}`): percentage of unstable microsatellite sites.")

cells = [
md("# {CASE}: {TUMOUR} vs {NORMAL}, structural variants, copy number, purity, MSI and HRD\n\n"
   "Companion to `{PREFIX}_step3.ipynb` (SNVs and indels). Method notes and conclusions: `{DOCS}`.\n\n"
   + "\n\n".join(inputs)),
code(f"""from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pysam
from IPython.display import Image, display
from scipy.stats import binomtest

pd.set_option("display.max_columns", None)
pd.set_option("display.max_colwidth", 80)

CASE_DIR = Path({cfg['case_dir']!r})
PATHS = {{k: Path(v) for k, v in {dict((k, str(v)) for k, v in P.items())!r}.items()}}
CHROMS = {cfg['autosomes'] + ['X']!r}  # autosomes in order, then X; unplaced contigs are dropped
AUTOSOMES = CHROMS[:-1]
MALE = {male!r}
LOOK_GENES = {look_genes!r}
GAIN, LOSS = 0.3, -0.3  # |log2| thresholds used for "altered" below
# Two hues for polarity, grey for neutral (validated pair from the step-3 notebook palette)
COLOUR = {{"gain": "#eb6834", "loss": "#2a78d6", "neutral": "#8a8a8a"}}"""),
]

# ---- Manta
if has["manta"]:
    cells += [
        md("## Manta: load and overview"),
        code("""sv = pd.read_csv(PATHS["sv_tsv"], sep="\\t", dtype={"chrom": str, "MATE_CHROM": str, "PICK_EXON": str, "PICK_INTRON": str})
SV_COLS = [c for c in ["chrom", "pos", "END", "SVTYPE", "SVLEN", "MATE_CHROM", "MATE_POS", "IMPRECISE", "SOMATICSCORE",
           "N_PR", "N_SR", "T_PR", "T_SR", "T_ALT", "T_ALT_FRAC", "PICK_GENE", "PICK_CONSEQUENCE", "PICK_EXON",
           "PICK_INTRON", "N_GENES"] if c in sv.columns]
sv_pass = sv[sv["FILTER"] == "PASS"]
display(pd.crosstab(sv["SVTYPE"], sv["FILTER"], margins=True))
sv_pass[SV_COLS]"""),
        md("""Look at each PASS call before trusting it. In FFPE exomes, deletions that remove exactly one intron (ends at
exon boundaries) and translocations joining a gene to its own paralogue are the signature of spliced cDNA in the
library, not genomic rearrangements. A call with alt reads in the normal is not somatic."""),
        code("""# Read support: tumour alt reads and fraction against Manta's somatic score, PASS and failing calls
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for flt, d in sv.groupby(sv["FILTER"].eq("PASS").map({True: "PASS", False: "failing"})):
    style = dict(marker="o" if flt == "PASS" else "x", s=40, color="#2a78d6" if flt == "PASS" else "#8a8a8a", label=flt)
    axes[0].scatter(d["SOMATICSCORE"], d["T_ALT"], **style)
    axes[1].scatter(d["SOMATICSCORE"], d["T_ALT_FRAC"], **style)
axes[0].set(xlabel="SOMATICSCORE", ylabel="Tumour alt reads (PR + SR)", yscale="log")
axes[1].set(xlabel="SOMATICSCORE", ylabel="Tumour alt fraction")
axes[0].legend(frameon=False)
for ax in axes:
    ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()"""),
        code("""# The failing calls
sv[sv["FILTER"] != "PASS"][["FILTER"] + SV_COLS]"""),
        code("""def sv_gene(name):
    \"\"\"Every Manta record whose VEP genes include this name.\"\"\"
    hit = sv["GENES"].fillna("").str.split(",").apply(lambda g: name in g)
    return sv[hit][["FILTER"] + SV_COLS]

pd.concat([sv_gene(g) for g in LOOK_GENES]) if LOOK_GENES else None"""),
    ]
    if has["manta_vcfs"]:
        cells += [
            md("""### Germline SVs near the somatic calls

Manta also writes diploid (germline) calls, for the pair and for the normal alone. A somatic call with a germline SV
nearby may be a germline event the somatic model missed in the normal, a polymorphic retrocopy or a mapping-prone
locus."""),
            code("""def germline_near(chrom, pos, window=1000):
    out = []
    for label, path in (("pair_diploid", PATHS["manta_pair"]), ("normal_diploid", PATHS["manta_normal"])):
        with pysam.VariantFile(str(path)) as vcf:
            for rec in vcf.fetch(chrom, max(0, pos - window), pos + window):
                out.append({"vcf": label, "chrom": rec.chrom, "pos": rec.pos, "SVTYPE": rec.info.get("SVTYPE"),
                            "END": rec.stop, "FILTER": ";".join(rec.filter.keys()),
                            "GT": [s.get("GT") for s in rec.samples.values()]})
    return pd.DataFrame(out)

near = []
for _, r in sv_pass.iterrows():
    g = germline_near(r["chrom"], int(r["pos"]))
    near.append({"chrom": r["chrom"], "pos": r["pos"], "SVTYPE": r["SVTYPE"], "PICK_GENE": r["PICK_GENE"],
                 "germline_within_1kb": len(g), "vcfs": ",".join(sorted(set(g["vcf"]))) if len(g) else ""})
pd.DataFrame(near)"""),
        ]
else:
    cells.append(code("""# No Manta input: an empty table keeps the plots below working
sv = pd.DataFrame(columns=["chrom", "pos", "END", "FILTER", "SVTYPE", "MATE_CHROM", "MATE_POS", "PICK_GENE", "GENES"])
sv_pass = sv"""))

# ---- CNVkit
if has["cnv"]:
    x_note = ("The patient is male. CNVkit puts a male X at about log2 -1 (one copy against a diploid baseline), so the "
              "X \"loss\" is expected. " if male else "")
    cells += [
        md("## CNVkit: load"),
        code(f"""def main_chroms(df, col="chromosome"):
    \"\"\"The main chromosomes, in order; the unplaced contigs are dropped.\"\"\"
    df = df[df[col].isin(CHROMS)].copy()
    df[col] = pd.Categorical(df[col], CHROMS, ordered=True)
    return df.sort_values([col, "start"])

read = lambda path: pd.read_csv(path, sep="\\t", dtype={{"chromosome": str}})
cnr_all, cns_all = read(PATHS["cnr"]), read(PATHS["cns"])
cnr, cns = main_chroms(cnr_all), main_chroms(cns_all)
normal_cns = main_chroms(read(PATHS["normal_cns"])) if {has['normal_cns']!r} else cns.iloc[:0]
cnr["kind"] = np.where(cnr["gene"] == "Antitarget", "antitarget", "target")
cns["length"] = cns["end"] - cns["start"]
cns["state"] = np.select([cns["log2"] >= GAIN, cns["log2"] <= LOSS], ["gain", "loss"], "neutral")
print(f"bins: {{len(cnr_all)}} ({{(cnr_all['gene'] == 'Antitarget').sum()}} antitarget); "
      f"{{len(cnr_all) - len(cnr)}} on unplaced contigs, dropped")
print(f"segments: {{len(cns_all)}} ({{len(cns_all) - len(cns)}} on unplaced contigs)")"""),
        md("""### Noise

The bin-to-bin SD (SD of the difference between neighbouring bins, divided by sqrt 2) measures noise independently
of real copy-number steps. Off-target bins are noisier in an exome. A single segment of a few bins with
|log2| < 0.3 is within noise."""),
        code("""def bin_sd(d):
    return np.nanstd(np.diff(d["log2"].to_numpy())) / np.sqrt(2)

pd.DataFrame({kind: {"bins": len(d), "bin_to_bin_SD": round(bin_sd(d), 3), "median_depth": d["depth"].median()}
              for kind, d in cnr.groupby("kind")}).T"""),
        code("""# Segment size and number of bins per segment
fig, axes = plt.subplots(1, 2, figsize=(11, 3.5))
axes[0].hist(np.log10(cns["length"]), bins=40, color="#8a8a8a")
axes[0].set(xlabel="log10 segment length (bp)", ylabel="Segments")
axes[1].hist(np.log10(cns["probes"]), bins=40, color="#8a8a8a")
axes[1].set(xlabel="log10 bins per segment", ylabel="Segments")
for ax in axes:
    ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()"""),
        md(f"""## Genome-wide profile

{x_note}X is left out of the altered fractions below."""),
        code("""chrom_len = cnr.groupby("chromosome", observed=True)["end"].max()
offset = chrom_len.cumsum() - chrom_len

def plot_genome(cnr, cns, title, ax, by_state=True):
    x = cnr["start"].to_numpy() + offset.reindex(cnr["chromosome"]).to_numpy()
    ax.scatter(x, cnr["log2"].clip(-2.5, 2.5), s=1, color="#c8c8c8", rasterized=True)
    for _, s in cns.iterrows():
        o = offset[s["chromosome"]]
        state = "gain" if s["log2"] >= GAIN else "loss" if s["log2"] <= LOSS else "neutral"
        state = state if by_state else "neutral"
        ax.plot([s["start"] + o, s["end"] + o], [s["log2"]] * 2, color=COLOUR[state], lw=2.5, solid_capstyle="round")
    for o in offset:
        ax.axvline(o, color="#e6e6e6", lw=0.8, zorder=0)
    ax.axhline(0, color="#666666", lw=0.8)
    ax.set_xticks(offset + chrom_len / 2, chrom_len.index, fontsize=7)
    ax.set(ylim=(-2.5, 2.5), xlim=(0, offset.iloc[-1] + chrom_len.iloc[-1]), ylabel="log2 ratio", title=title)
    ax.spines[["top", "right"]].set_visible(False)

fig, ax = plt.subplots(figsize=(16, 4))
plot_genome(cnr, cns, "Tumour vs normal: bins (grey) and segments (orange gain, blue loss, |log2| >= 0.3)", ax)
plt.tight_layout()"""),
    ]
    if has["normal_cns"]:
        cells.append(code("""# The normal alone: about one segment per chromosome means the tumour pattern is not a capture artefact. Without
# a matched reference its baseline need not sit at 0, so segments are not coloured by state.
fig, ax = plt.subplots(figsize=(16, 2.8))
plot_genome(cnr.iloc[:0], normal_cns, "Normal alone: segments", ax, by_state=False)
ax.set_ylim(-1.5, 1.5)
plt.tight_layout()"""))
    cells += [
        code("""# Per chromosome: segments and fraction of length gained or lost (and normal-alone segments, if available)
def frac(d, mask):
    return round((d["length"] * mask).sum() / d["length"].sum(), 3)

per_chrom = pd.DataFrame({
    "segments": cns.groupby("chromosome", observed=True).size(),
    "normal_segments": normal_cns.groupby("chromosome", observed=True).size(),
    "frac_gain": cns.groupby("chromosome", observed=True).apply(lambda d: frac(d, d["log2"] >= GAIN)),
    "frac_loss": cns.groupby("chromosome", observed=True).apply(lambda d: frac(d, d["log2"] <= LOSS)),
    "weighted_mean_log2": cns.groupby("chromosome", observed=True).apply(
        lambda d: round(np.average(d["log2"], weights=d["length"]), 3)),
})
auto = cns[cns["chromosome"] != "X"]
print(f"Fraction of the autosomes altered (|log2| >= {GAIN}): gain {frac(auto, auto['log2'] >= GAIN)}, "
      f"loss {frac(auto, auto['log2'] <= LOSS)}")
per_chrom.sort_values("segments", ascending=False)"""),
        code("""# The largest altered autosomal segments, with at least 20 bins
auto[(auto["state"] != "neutral") & (auto["probes"] >= 20)].sort_values("length", ascending=False).head(30)"""),
        md("""## One chromosome

`plot_chrom(chrom, start, end)` draws the bins, the tumour segments and the normal-alone segments, and marks the
Manta PASS breakpoints (purple dashed) and the failing ones (dotted). `seg_at(chrom, pos)` gives the CNVkit segment
under a position."""),
        code("""def plot_chrom(chrom, start=None, end=None, ax=None):
    chrom = str(chrom)
    b = cnr[cnr["chromosome"] == chrom]
    s, p = cns[cns["chromosome"] == chrom], normal_cns[normal_cns["chromosome"] == chrom]
    start = b["start"].min() if start is None else start
    end = b["end"].max() if end is None else end
    b = b[(b["end"] > start) & (b["start"] < end)]
    if ax is None:
        _, ax = plt.subplots(figsize=(14, 3.8))
    for kind, colour in (("antitarget", "#e0e0e0"), ("target", "#b5b5b5")):
        d = b[b["kind"] == kind]
        ax.scatter(d["start"] / 1e6, d["log2"].clip(-2.5, 2.5), s=4, color=colour, label=f"{kind} bins")
    for _, r in s.iterrows():
        ax.plot([r["start"] / 1e6, r["end"] / 1e6], [r["log2"]] * 2, color=COLOUR[r["state"]], lw=3,
                solid_capstyle="round")
    for i, (_, r) in enumerate(p.iterrows()):
        ax.plot([r["start"] / 1e6, r["end"] / 1e6], [r["log2"]] * 2, color="#333333", lw=1, ls="--",
                label="normal alone" if i == 0 else None)
    for _, r in sv[sv["chrom"] == chrom].iterrows():
        ls = "--" if r["FILTER"] == "PASS" else ":"
        for x in {r["pos"], r["END"]}:
            if pd.notna(x) and start <= x <= end:
                ax.axvline(x / 1e6, color="#6b3fa0", lw=1, ls=ls)
    ax.axhline(0, color="#666666", lw=0.8)
    ax.set(xlim=(start / 1e6, end / 1e6), ylim=(-2.5, 2.5), xlabel=f"chr{chrom} (Mb)", ylabel="log2 ratio")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    return ax

def seg_at(chrom, pos):
    s = cns[(cns["chromosome"] == str(chrom)) & (cns["start"] <= pos) & (cns["end"] >= pos)]
    return (round(s["log2"].iloc[0], 2), s["state"].iloc[0]) if len(s) else (np.nan, "no segment")"""),
    ]
    for chrom, start, end in cfg["plot_regions"]:
        cells.append(code(f"""plot_chrom({str(chrom)!r}, {start!r}, {end!r})
cns[(cns["chromosome"] == {str(chrom)!r})""" + (f""" & (cns["end"] > {start}) & (cns["start"] < {end})""" if start is not None else "") + "]"))
    if has["manta"]:
        cells.append(code("""# Copy-number segment under each PASS SV breakpoint (and its mate or end)
rows = []
for _, r in sv_pass.iterrows():
    other = (r["MATE_CHROM"], r["MATE_POS"]) if r["SVTYPE"] == "BND" else (r["chrom"], r["END"])
    rows.append({"chrom": r["chrom"], "pos": r["pos"], "SVTYPE": r["SVTYPE"], "PICK_GENE": r["PICK_GENE"],
                 "log2_at_pos": seg_at(r["chrom"], r["pos"])[0], "state_at_pos": seg_at(r["chrom"], r["pos"])[1],
                 "log2_at_other_end": seg_at(*other)[0] if pd.notna(other[1]) else np.nan})
pd.DataFrame(rows)"""))

    if has["coords"]:
        cells += [
            md("""## Copy number per gene

Each gene gets the CNVkit segment covering its midpoint, plus the median log2 and count of the target bins inside
it. Genes with no target bin have no direct measurement; their value comes from the surrounding segment only."""),
            code("""genes = pd.read_csv(PATHS["gene_coords"], sep="\\t", dtype={"chrom": str})
genes = genes[genes["chrom"].isin(CHROMS)].copy()
genes["mid"] = (genes["start"] + genes["end"]) // 2
seg_cols = ["log2", "cn", "state", "start", "end", "probes"]
parts = []
for chrom, g in genes.groupby("chrom"):
    s = cns[cns["chromosome"] == chrom].reset_index(drop=True)
    if s.empty:
        continue
    i = np.searchsorted(s["start"].to_numpy(), g["mid"].to_numpy(), side="right") - 1
    ok = (i >= 0) & (g["mid"].to_numpy() <= s["end"].to_numpy()[np.clip(i, 0, None)])
    seg = s.loc[np.clip(i, 0, None), seg_cols].reset_index(drop=True)
    seg.columns = ["seg_" + c for c in seg_cols]
    seg[~ok] = np.nan
    parts.append(pd.concat([g.reset_index(drop=True), seg], axis=1))
gene_cn = pd.concat(parts, ignore_index=True)

# Target bins inside each gene
tb = cnr[cnr["kind"] == "target"]
stats = []
for chrom, g in gene_cn.groupby("chrom"):
    b = tb[tb["chromosome"] == chrom]
    starts, log2 = b["start"].to_numpy(), b["log2"].to_numpy()
    lo = np.searchsorted(starts, g["start"].to_numpy())
    hi = np.searchsorted(starts, g["end"].to_numpy(), side="right")
    stats += [(idx, h - l, np.median(log2[l:h]) if h > l else np.nan) for idx, l, h in zip(g.index, lo, hi)]
stats = pd.DataFrame(stats, columns=["idx", "target_bins", "gene_bin_log2"]).set_index("idx")
gene_cn = gene_cn.join(stats)
gene_cn["gene_bin_log2"] = gene_cn["gene_bin_log2"].round(3)
GENE_COLS = ["GENE_NAME", "HUMAN_SYMBOL", "biotype", "chrom", "start", "end", "target_bins", "gene_bin_log2",
             "seg_log2", "seg_cn", "seg_state", "seg_start", "seg_end", "seg_probes"]
gene_cn.groupby("seg_state")["biotype"].value_counts().unstack(fill_value=0)[["protein_coding"]]"""),
            code("""def cn_gene(*names):
    hit = gene_cn["GENE_NAME"].isin(names) | gene_cn["HUMAN_SYMBOL"].isin(names)
    return gene_cn[hit][GENE_COLS]

cn_gene(*LOOK_GENES)"""),
        ]

# ---- FACETS
if has["facets"]:
    doubtful = cfg["facets_doubtful"]
    cells += [
        md(f"""## Purity, ploidy and allele-specific copy number (FACETS)

FACETS runs on the tumour against the normal at germline heterozygous SNPs{' (autosomes only: the patient is male)' if male else ''}.
Each segment gets:
- a log ratio (`cnlr.median`) and an allelic imbalance (`mafR` is about the squared log-odds ratio, so
  `lor` = sqrt(mafR) below);
- a total and minor copy number (`tcn.em`, `lcn.em`) and a cell fraction (`cf.em`).

Purity is the fraction of cells that are tumour. A tumour with ploidy above 2 supplies more than that fraction of
the DNA."""),
        code(f"""FACETS_DIR = PATHS["facets_dir"]
summaries = {{}}
for cval in {cfg['facets_cvals']!r}:
    f = FACETS_DIR / f"{fp}.facets.cval{{cval}}.summary.tsv"
    if f.exists():
        s = pd.read_csv(f, sep="\\t", header=None, index_col=0)[1]
        summaries[cval] = s
        print(f"cval {{cval}}: purity {{float(s['purity']):.3f}}, ploidy {{float(s['ploidy']):.2f}}, dipLogR {{float(s['dipLogR']):.3f}}")
fac = pd.read_csv(FACETS_DIR / "{fp}.facets.cval{cval}.segments.tsv", sep="\\t")
fac["chrom"] = fac["chrom"].astype(str)
fac["len_Mb"] = (fac["end"] - fac["start"]) / 1e6
fac["lor"] = np.sqrt(fac["mafR"].clip(lower=0))
PURITY, PLOIDY = float(summaries[{cval}]["purity"]), float(summaries[{cval}]["ploidy"])
HALF = 2 if PLOIDY > 2.7 else 1  # balanced baseline: 2:2 in a genome-doubled tumour, else 1:1
print(f"working model: purity {{PURITY:.2f}}, ploidy {{PLOIDY:.2f}}, baseline {{HALF}}:{{HALF}}; tumour share of the DNA "
      f"{{PURITY * PLOIDY / (PURITY * PLOIDY + 2 * (1 - PURITY)):.2f}}")
png = FACETS_DIR / "{fp}.facets.cval{cval}.png"
if png.exists():
    display(Image(png, width=1000))
fac.groupby(["tcn.em", "lcn.em"], dropna=False)["len_Mb"].sum().round(1).sort_values(ascending=False).to_frame()"""),
        md("""### Diploid or genome-doubled?

To compare the two models, fix each one's balanced baseline (1:1 diploid, 2:2 doubled), scan purity, and give every
FACETS segment its best integer state, scored on both log ratio and allelic imbalance. For M:m copies at purity p
(the normal adds one copy of each allele):
- log ratio = log2((2(1-p) + p(M+m)) / 2) + c
- lor = |ln(((1-p) + pM) / ((1-p) + pm))|

The baseline offset c puts the balanced state at the median log ratio of long segments with no allelic imbalance.
Balanced losses (log2 well below 0 with no imbalance) and states like 2:1 or 3:0 fit only a doubled genome."""),
        code("""def expect(p, M, m):
    total = 2 * (1 - p) + p * (M + m)
    return np.log2(total / 2), abs(np.log(((1 - p) + p * M) / ((1 - p) + p * m)))

balanced = fac[(fac["mafR"] < 0.05) & (fac["len_Mb"] > 40)]
base = balanced["cnlr.median"].median() if len(balanced) else np.average(fac["cnlr.median"], weights=fac["len_Mb"])

def fit(p, half, max_cn):
    \"\"\"Best integer state and error per segment at purity p, balanced baseline half:half.\"\"\"
    c = base - expect(p, half, half)[0]
    states = [(M, m) for M in range(max_cn + 1) for m in range(M + 1) if M + m <= max_cn]
    lr = np.array([expect(p, M, m)[0] + c for M, m in states])
    lor = np.array([expect(p, M, m)[1] for M, m in states])
    err = ((lr[None] - fac["cnlr.median"].to_numpy()[:, None]) / 0.1) ** 2 + \\
          ((lor[None] - fac["lor"].to_numpy()[:, None]) / 0.12) ** 2
    best = err.argmin(axis=1)
    return [f"{states[i][0]}:{states[i][1]}" for i in best], err[np.arange(len(fac)), best]

MODELS = {"diploid": (1, 4), "doubled": (2, 8)}
grid = np.round(np.arange(0.10, 1.00, 0.01), 2)
scan = pd.DataFrame({name: [(fit(p, half, mx)[1] * fac["len_Mb"]).sum() for p in grid]
                     for name, (half, mx) in MODELS.items()}, index=grid)
best_p = scan.idxmin()
print("best purity per model:", best_p.to_dict(), "; length-weighted error:", scan.min().round(0).to_dict())
cmp = fac[["chrom", "start", "end", "len_Mb", "cnlr.median", "lor", "tcn.em", "lcn.em", "cf.em"]].copy()
cmp["dlogR"] = cmp["cnlr.median"] - base
for name, (half, mx) in MODELS.items():
    cmp[f"{name}_state"], err = fit(best_p[name], half, mx)
    cmp[f"{name}_err"] = err.round(1)
ax = scan.plot(figsize=(7, 3), color=["#8a8a8a", "#2a78d6"])
ax.axvline(PURITY, color="#eb6834", lw=1, ls="--", label=f"FACETS purity {PURITY:.2f}")
ax.set(xlabel="purity", ylabel="length-weighted error", yscale="log")
ax.legend(frameon=False)
ax.spines[["top", "right"]].set_visible(False)
cmp[cmp["len_Mb"] > 3].round(2)"""),
        md("""Segments where FACETS's EM state disagrees with its allelic imbalance (for example LOH called at low cell
fraction with a small `lor`) should not be trusted; list them in the case config's `facets_doubtful`."""),
    ]
    if has["snv"]:
        cells += [
            md("""### SNV VAFs at the FACETS purity

In a balanced region of the working model, a clonal mutation on k of the 2·HALF copies is expected at VAF
k·p / (2(1-p) + 2·HALF·p). In a doubled tumour, mutations from before the doubling sit at k = 2, those from after it
at k = 1. The histogram shows the HIGH_CONF_BOTH_PASS SNVs in balanced FACETS segments."""),
            code("""snv_all = pd.read_csv(PATHS["snv_tsv"], sep="\\t", dtype={"chrom": str}, low_memory=False)
snv = snv_all[snv_all["TIER"].isin(["HIGH_CONF_BOTH_PASS", "BOTH_PASS"]) & (snv_all["TYPE"] == "SNV")].copy()
snv["VAF"] = snv[["M2_T_RVAF", "S2_T_VAF"]].mean(axis=1)

def fac_at(chrom, pos):
    s = cmp[(cmp["chrom"] == str(chrom)) & (cmp["start"] <= pos) & (cmp["end"] >= pos)]
    return s.iloc[0] if len(s) else None

def balanced_at(chrom, pos):
    s = fac_at(chrom, pos)
    return s is not None and abs(s["dlogR"]) < 0.1 and s["lor"] < 0.15

hc = snv[(snv["TIER"] == "HIGH_CONF_BOTH_PASS") & (snv["chrom"] != "X")]
neutral = hc[[balanced_at(c, p) for c, p in zip(hc["chrom"], hc["pos"])]]
total = 2 * (1 - PURITY) + 2 * HALF * PURITY
fig, ax = plt.subplots(figsize=(10, 3.2))
ax.hist(neutral["VAF"], bins=np.arange(0, 0.7, 0.025), color="#8a8a8a", label="balanced segments, HIGH_CONF_BOTH_PASS")
for k in range(1, HALF + 1):
    ax.axvline(k * PURITY / total, color="#2a78d6", ls=":" if k == 1 else "--", lw=1.5,
               label=f"{k} of {2 * HALF} copies ({k * PURITY / total:.2f})")
ax.set(xlabel="tumour VAF", ylabel="SNVs")
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False)
print(f"{len(neutral)} SNVs in balanced segments: median VAF {neutral['VAF'].median():.2f}")"""),
        ]
        if driver:
            cells[-1]["source"] += f"""
d = snv_all[(snv_all["chrom"] == {str(driver['chrom'])!r}) & (snv_all["pos"] == {driver['pos']})]
if len(d):
    d = d.iloc[0]
    ax.axvline(d["M2_T_RVAF"], color="#eb6834", lw=2, label=f"{driver['label']} ({{d['M2_T_RVAF']:.2f}})")
ax.legend(frameon=False)"""
            cells += [
                md(f"""### {driver['label']}

The driver's VAF is tested against every placement of the mutation on the candidate allelic states at its locus
(FACETS EM and the two refits), at the FACETS purity. A wild-type copy is left wherever fewer than all copies are
mutant."""),
                code(f"""row = snv_all[(snv_all["chrom"] == {str(driver['chrom'])!r}) & (snv_all["pos"] == {driver['pos']})].iloc[0]
alt, depth = int(row["M2_T_ALT"]), int(round(row["M2_T_ALT"] / row["M2_T_RVAF"]))
ci = binomtest(alt, depth).proportion_ci()
print(f"{driver['label']}: tier {{row['TIER']}}, VAF {{alt}}/{{depth}} = {{alt / depth:.3f}}, 95% CI {{ci.low:.2f}}-{{ci.high:.2f}}")
seg = fac_at({str(driver['chrom'])!r}, {driver['pos']})
display(seg.to_frame().T.round(2))
cands = {{}}
if pd.notna(seg["lcn.em"]):
    cands[f"{{int(seg['tcn.em']) - int(seg['lcn.em'])}}:{{int(seg['lcn.em'])}}"] = ["FACETS EM"]
for model in ("diploid", "doubled"):
    cands.setdefault(seg[f"{{model}}_state"], []).append(f"{{model}} refit")
cands = {{state: ", ".join(src) for state, src in cands.items()}}
rows = []
for state, source in cands.items():
    M, m = map(int, state.split(":"))
    for k in range(1, M + m + 1):
        v = PURITY * k / (2 * (1 - PURITY) + PURITY * (M + m))
        rows.append({{"state": state, "from": source, "mutant_copies": f"{{k}} of {{M + m}}",
                     "wild_type_left": k < M + m, "expected_VAF": round(v, 3),
                     "binomial_p": binomtest(alt, depth, min(v, 1)).pvalue}})
scen = pd.DataFrame(rows).sort_values("binomial_p", ascending=False)
scen["binomial_p"] = scen["binomial_p"].map(lambda x: f"{{x:.1e}}")
scen"""),
            ]
            if has["cnv"]:
                pos = driver["pos"]
                cells.append(code(f"""ax = plot_chrom({str(driver['chrom'])!r}, {max(0, pos - 1_500_000)}, {pos + 1_500_000})
ax.axvline({pos} / 1e6, color="#eb6834", lw=1.5)
cns[(cns["chromosome"] == {str(driver['chrom'])!r}) & (cns["end"] > {pos - 1_000_000}) & (cns["start"] < {pos + 1_000_000})]"""))

# ---- Panel copy number
if panel and has["cnv"] and has["coords"]:
    genes, title, source = panel
    cells += [
        md(f"""## {title}: copy number

{source}"""),
        code(f"""PANEL = {genes!r}
panel = cn_gene(*PANEL)
panel.insert(0, "panel", panel["HUMAN_SYMBOL"].where(panel["HUMAN_SYMBOL"].isin(PANEL), panel["GENE_NAME"]).map(PANEL))
panel[panel["biotype"] == "protein_coding"].sort_values(["panel", "chrom", "start"])"""),
    ]
if has["cnv"] and has["coords"]:
    cells += [
        code("""# Protein-coding genes in the strongest altered segments (|log2| >= 0.5, at least 20 bins), by segment
strong = gene_cn[(gene_cn["biotype"] == "protein_coding") & (gene_cn["seg_log2"].abs() >= 0.5) & (gene_cn["seg_probes"] >= 20)]
(strong.groupby(["chrom", "seg_start", "seg_end", "seg_log2", "seg_state"])["GENE_NAME"]
       .agg(n_genes="size", genes=lambda g: ",".join(g[:25]) + (" ..." if len(g) > 25 else "")).reset_index())"""),
        code("""def region(chrom, start, end):
    \"\"\"Segments and protein-coding genes in a region.\"\"\"
    s = cns[(cns["chromosome"] == str(chrom)) & (cns["end"] > start) & (cns["start"] < end)]
    g = gene_cn[(gene_cn["chrom"] == str(chrom)) & (gene_cn["end"] > start) & (gene_cn["start"] < end)
                & (gene_cn["biotype"] == "protein_coding")]
    display(s)
    return g[GENE_COLS]"""),
    ]

# ---- HRD
if has["facets"]:
    cells += [
        md("""## HR deficiency

### Genomic scar counts

These are FACETS-based approximations of the HRD-LOH and LST components:
- **HRD-LOH:** LOH segments longer than 15 Mb that are not whole-chromosome.
- **LST:** state changes between neighbours of at least 10 Mb, after dropping segments under 3 Mb.
- **TAI** is not computed: it needs telomere-to-centromere arms, and canine autosomes are acrocentric.

The human HRD threshold (HRD-LOH + TAI + LST at least 42) is the only reference available. It has not been
validated in dogs."""),
        code(f"""DOUBTFUL = {doubtful!r}  # FACETS segments not to trust: [chrom, start, end]
seg = fac[fac["tcn.em"].notna()].copy()
chrom_len_mb = seg.groupby("chrom")["end"].max() / 1e6
loh = seg[(seg["lcn.em"] == 0) & (seg["tcn.em"] > 0) & (seg["len_Mb"] > 15)
          & (seg["len_Mb"] < 0.9 * seg["chrom"].map(chrom_len_mb))]
in_doubtful = loh.apply(lambda r: any(str(c) == r["chrom"] and r["start"] < e and r["end"] > s for c, s, e in DOUBTFUL), axis=1)
lst = 0
for ch, g in seg.groupby("chrom"):
    merged = []
    for _, r in g[g["len_Mb"] >= 3].iterrows():
        state = f"{{r['tcn.em']:.0f}}:{{r['lcn.em']}}"
        if merged and merged[-1][0] == state:
            merged[-1][1] += r["len_Mb"]
        else:
            merged.append([state, r["len_Mb"]])
    lst += sum(a[1] >= 10 and b[1] >= 10 for a, b in zip(merged, merged[1:]))
HRD_LOH, HRD_LOH_CLEAN, LST = len(loh), int((~in_doubtful).sum()), lst
print(f"HRD-LOH: {{HRD_LOH}} ({{HRD_LOH_CLEAN}} outside the doubtful FACETS calls); LST: {{LST}}")
loh.assign(doubtful=in_doubtful)[["chrom", "start", "end", "len_Mb", "tcn.em", "lcn.em", "cf.em", "lor", "doubtful"]].round(2)"""),
    ]
HR = hr_genes()
if has["snv"] or has["hr_germline"] or (has["facets"] and has["coords"]):
    cells += [md("""### Mutations in HR genes

A 41-gene HR list is checked for somatic SNVs and indels (step-3 table), Manta SVs, germline variants in the normal
and the FACETS state at each gene."""),
              code(f"""HR = {HR!r}""")]
if has["snv"]:
    cells.append(code("""allcalls = pd.read_csv(PATHS["snv_tsv"], sep="\\t", dtype={"chrom": str}, low_memory=False)
in_hr = allcalls["HUMAN_SYMBOL"].isin(HR) | allcalls["GENE_NAME"].isin(HR)
hr_som = allcalls[in_hr]
print("somatic calls in HR genes, tier by impact:")
display(pd.crosstab(hr_som["TIER"], hr_som["IMPACT"]))
print("passing tiers or coding (HIGH/MODERATE):")
hr_som[(hr_som["TIER"] != "NO_PASS") | hr_som["IMPACT"].isin(["HIGH", "MODERATE"])][
    [c for c in ["chrom", "pos", "ref", "alt", "TIER", "GENE_NAME", "HUMAN_SYMBOL", "Consequence", "IMPACT", "HGVSp",
     "M2_T_ALT", "M2_T_DP", "S2_T_ALT", "S2_T_DP", "PBMC_GERMLINE"] if c in allcalls.columns]]"""))
if has["manta"]:
    cells.append(code("""hr_sv = sv[sv["GENES"].fillna("").apply(lambda s: any(g in HR for g in s.split(",")))]
print(f"Manta somatic SVs touching an HR gene: {len(hr_sv)}")
hr_sv[["FILTER"] + SV_COLS]"""))
if has["hr_germline"]:
    cells += [
        code(f"""germ = pd.read_csv(PATHS["hr_germline_tsv"], sep="\\t", dtype=str)
germ.columns = [c.split("]")[-1] for c in germ.columns]  # bcftools query headers: #[1]CHROM -> CHROM
{"names = pd.read_csv(PATHS['gene_coords'], sep=chr(9), usecols=['gene_id', 'GENE_NAME', 'HUMAN_SYMBOL'])" if has["coords"] else "names = None"}
if names is not None and "Gene" in germ.columns:
    germ = germ.merge(names, left_on="Gene", right_on="gene_id", how="left")
coding = germ[germ["IMPACT"].isin(["HIGH", "MODERATE"])]
print(f"{{len(germ)}} normal PASS variants in HR genes; {{len(coding)}} coding (HIGH/MODERATE), "
      f"{{(coding['IMPACT'] == 'HIGH').sum()}} HIGH")
coding"""),
        md("""Check every germline HIGH-impact call before reading it as loss of function: homozygous frameshifts in GC-rich
first exons or homopolymers, pairs of frameshifts that restore the frame, and alleles common in Dog10K are
reference or annotation artefacts, not disease alleles."""),
    ]
if has["facets"] and has["coords"]:
    cells.append(code("""# FACETS copy number at the HR genes
gc_hr = pd.read_csv(PATHS["gene_coords"], sep="\\t", dtype={"chrom": str})
gc_hr = gc_hr[(gc_hr["HUMAN_SYMBOL"].isin(HR) | gc_hr["GENE_NAME"].isin(HR)) & (gc_hr["biotype"] == "protein_coding")
              & gc_hr["chrom"].isin(set(fac["chrom"]))]
def facets_at(ch, pos):
    s = fac[(fac["chrom"] == ch) & (fac["start"] <= pos) & (fac["end"] >= pos)]
    return (f"{s['tcn.em'].iloc[0]:.0f}:{s['lcn.em'].iloc[0]}", round(s["lor"].iloc[0], 2)) if len(s) else ("-", None)
gc_hr[["facets_tcn:lcn", "lor"]] = [facets_at(c, (s + e) // 2) for c, s, e in zip(gc_hr["chrom"], gc_hr["start"], gc_hr["end"])]
gc_hr["LOH"] = gc_hr["facets_tcn:lcn"].str.endswith(":0.0")
gc_hr[["GENE_NAME", "HUMAN_SYMBOL", "chrom", "start", "facets_tcn:lcn", "lor", "LOH"]].sort_values(["LOH", "chrom"], ascending=[False, True])"""))

# ---- MSI
if has["msi"]:
    cells += [
        md("""## MSIsensor-pro

Each site gets a repeat-length distribution in each sample, and the score is the percentage of unstable sites.
The 3.5% cut-off used for paired human exomes is the only reference; there is no validated canine threshold."""),
        code("""msi = pd.read_csv(PATHS["msi"], sep="\\t")
MSI_PCT = float(msi.iloc[0, -1])
print(f"MSI score {MSI_PCT:.2f}%: {'MSI-high by the human cut-off' if MSI_PCT >= 3.5 else 'microsatellite stable by the human cut-off'}")
msi"""),
    ]

# ---- Summary
cells += [
    md("## Summary\n\nComputed from the sections above; the interpretation belongs in `{DOCS}`."),
    code("""summary = {}
if "PURITY" in globals():
    summary["Purity / ploidy (FACETS)"] = f"{PURITY:.2f} / {PLOIDY:.2f} ({'genome-doubled' if HALF == 2 else 'near-diploid'})"
    summary["Refit best purity (diploid, doubled)"] = f"{best_p['diploid']:.2f}, {best_p['doubled']:.2f}; error " + \\
        f"{scan['diploid'].min():,.0f} vs {scan['doubled'].min():,.0f}"
if "scen" in globals():
    top = scen.iloc[0]
    summary["Driver, best-fitting state"] = f"{top['state']}, {top['mutant_copies']} mutant (p {top['binomial_p']})" + \\
        ("" if top["wild_type_left"] else ", no wild type left")
if "cns" in globals():
    summary["Autosomes altered (CNVkit, |log2| >= 0.3)"] = f"gain {frac(auto, auto['log2'] >= GAIN)}, loss {frac(auto, auto['log2'] <= LOSS)}"
if "sv_pass" in globals() and len(sv):
    summary["Manta PASS SVs"] = len(sv_pass)
if "LST" in globals():
    summary["HRD scar (human threshold 42)"] = f"HRD-LOH {HRD_LOH_CLEAN}-{HRD_LOH}, LST {LST}"
if "MSI_PCT" in globals():
    summary["MSI (MSIsensor-pro)"] = f"{MSI_PCT:.2f}% unstable sites"
pd.Series(summary, name="value").to_frame()"""),
]

write(cells, cfg, out, f"{prefix}_sv_cnv_facets_msi_hrd.ipynb", "sv_cnv")
