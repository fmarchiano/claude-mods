"""Write a gene-coordinate table (gene_id, GENE_NAME, HUMAN_SYMBOL, biotype, chrom, start, end) for the CNV notebook,
from the Ensembl 116 CanFam4 GTF and the gene-names table (CanFam4 symbol, else orthologue)."""
import argparse
import gzip

import pandas as pd

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--gtf", required=True)
parser.add_argument("--gene-names", required=True)
parser.add_argument("--out", required=True)
args = parser.parse_args()

rows = []
with gzip.open(args.gtf, "rt") as gtf:
    for line in gtf:
        if line.startswith("#"):
            continue
        f = line.split("\t")
        if f[2] != "gene":
            continue
        gene_id = f[8].split('gene_id "')[1].split('"')[0]
        rows.append((gene_id, f[0], int(f[3]), int(f[4])))
genes = pd.DataFrame(rows, columns=["gene_id", "chrom", "start", "end"])
names = pd.read_csv(args.gene_names, sep="\t", usecols=["gene_id", "biotype", "GENE_NAME", "HUMAN_SYMBOL"])
genes = genes.merge(names, on="gene_id", how="left")
genes["GENE_NAME"] = genes["GENE_NAME"].fillna(genes["gene_id"])
genes[["gene_id", "GENE_NAME", "HUMAN_SYMBOL", "biotype", "chrom", "start", "end"]].to_csv(args.out, sep="\t", index=False)
print(f"{args.out}: {len(genes)} genes")
