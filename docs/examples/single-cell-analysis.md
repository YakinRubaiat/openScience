---
layout: default
title: "Example: Single-Cell RNA-seq Analysis"
parent: Examples
nav_order: 2
description: "End-to-end scRNA-seq workflow from raw counts to cell-type annotation"
---

# Single-Cell RNA-seq Analysis

A complete workflow: from a 10x Genomics `.h5ad` file to annotated cell types with marker genes and pathway enrichment.

---

## 🎯 The Goal

> *Analyze a 10k PBMC dataset, identify cell types, find markers, and prepare figures and methods for publication.*

By the end:

- QC-filtered, normalized, clustered dataset
- UMAP, violin plots, heatmap (publication quality)
- Cell-type annotations based on canonical markers
- GSEA on differential markers
- Complete methods section

**Time**: ~20 minutes

---

## 📋 Prerequisites

- openScience with the `bio` extra: `pip install -e ".[bio]"`
- ~16 GB RAM
- Optional: GPU not needed

---

## ✅ Step 0 — Download the data

```bash
mkdir -p data/raw

curl -L -o data/raw/pbmc_10k.h5ad \
  https://cf.10xgenomics.com/samples/cell-exp/3.0.0/pbmc_10k_v3/pbmc_10k_v3_filtered_feature_bc_matrix.h5ad
```

---

## ✅ Step 1 — QC and clustering

Create `scrna_analysis.py`:

```python
from openscience import ScienceSession

session = ScienceSession(project_dir=".")

# 1. Load
session.load_data("data/raw/pbmc_10k.h5ad", format="anndata", name="pbmc")

# 2. QC
print("📊 Running quality control...")
qc = session.analyze(
    task=(
        "QC filtering: keep cells with 200–6000 genes detected, "
        "<20% mitochondrial reads. Filter genes seen in <3 cells. "
        "Generate QC report with violin plots pre/post filtering."
    ),
    specialist="qc_analyzer",
    min_genes=200,
    max_genes=6000,
    max_pct_mito=20,
    min_cells=3,
)

# 3. Normalize + cluster
print("🧬 Normalizing and clustering...")
clustered = session.analyze(
    task=(
        "Normalize (CP10k + log1p), select 2000 highly-variable genes, "
        "scale, PCA, build kNN graph, Leiden clustering, UMAP embedding."
    ),
    specialist="scanpy_specialist",
    n_top_genes=2000,
    n_neighbors=10,
    n_pcs=40,
    resolution=0.5,
)
```

Key parameters explained:

| Parameter | Value | Why |
|-----------|-------|-----|
| `min_genes=200` | 200 | Removes empty droplets / dying cells |
| `max_genes=6000` | 6000 | Removes likely doublets |
| `max_pct_mito=20` | 20% | Removes stressed/dying cells |
| `n_neighbors=10` | 10 | Balance local vs global structure |
| `n_pcs=40` | 40 | Captures most variance after HVG |
| `resolution=0.5` | 0.5 | Moderate cluster granularity |

---

## ✅ Step 2 — Identify cell types

```python
# 4. Find markers per cluster
print("🔍 Finding cluster markers...")
markers = session.analyze(
    task="Find marker genes for each Leiden cluster (Wilcoxon, FDR-corrected)",
    specialist="scanpy_specialist",
    method="wilcoxon",
    corr_method="benjamini-hochberg",
    min_log2fc=0.5,
    max_pval_adj=0.05,
)

# 5. Annotate based on canonical markers
print("🏷️  Annotating cell types...")
annotated = session.analyze(
    task=(
        "Annotate PBMC clusters using canonical markers: "
        "CD3D/CD3E→T cells, CD19/MS4A1→B cells, CD14→Mono, "
        "NCAM1→NK, CD34→HSC, IL3RA→pDC. "
        "Use score_cells + majority vote."
    ),
    specialist="scanpy_specialist",
    marker_database="panglao",
)
```

The `scanpy_specialist` agent compares cluster markers against curated databases (PanglaoDB, CellMarker) and proposes annotations with supporting evidence.

---

## ✅ Step 3 — Visualize

```python
# 6. Figures
print("📈 Generating figures...")

# UMAP with annotations
session.visualize(
    annotated,
    type="umap",
    color="cell_type",
    style="publication",
    output="figures/umap_celltypes.pdf",
    frameon=False,
    legend_loc="on data",
)

# Marker heatmap
session.visualize(
    markers,
    type="heatmap",
    n_genes=10,
    groupby="cell_type",
    output="figures/marker_heatmap.pdf",
    style="publication",
)

# Violin plot of key markers
session.visualize(
    annotated,
    type="violin",
    keys=["CD3D", "MS4A1", "CD14", "NCAM1"],
    groupby="cell_type",
    output="figures/marker_violin.pdf",
)
```

---

## ✅ Step 4 — Pathway analysis

```python
# 7. Differential expression between cell types
print("🧪 Differential analysis...")
de = session.analyze(
    task="Pairwise DE between cell types, Wilcoxon + FDR",
    specialist="scanpy_specialist",
    groupby="cell_type",
)

# 8. GSEA on top markers
print("🔬 Pathway enrichment...")
gsea = session.analyze(
    task="GSEA on top 100 markers per cell type, MSigDB Hallmark",
    specialist="gsea_analyzer",
    gene_sets="MSigDB_Hallmark_2020",
    n_perm=1000,
)

# Enrichment plots
session.visualize(
    gsea,
    type="dotplot",
    top_pathways=5,
    output="figures/gsea_dotplot.pdf",
)
```

---

## ✅ Step 5 — Document

```python
# 9. Methods
print("✍️  Writing methods section...")
methods = session.write_methods(clustered, style="nature")
with open("results/methods.md", "w") as f:
    f.write(methods)

# 10. Results narrative
results_text = session.analyze(
    task=(
        "Summarize key findings: number of cells, clusters, "
        "top marker for each, notable pathway enrichments. "
        "Two paragraphs, Nature style."
    ),
    specialist="results_writer",
    inputs=[clustered, markers, de, gsea],
)
with open("results/results.md", "w") as f:
    f.write(results_text)

# 11. Save session
session.save("pbmc_analysis.pkl")
```

---

## 📂 Resulting File Tree

```
.
├── pbmc_analysis.pkl          ← restored later with ScienceSession.load()
├── data/raw/pbmc_10k.h5ad     ← source (immutable)
├── data/processed/
│   ├── adata_qc.h5ad
│   ├── adata_clustered.h5ad
│   └── adata_annotated.h5ad
├── results/
│   ├── markers_per_cluster.csv
│   ├── de_results.csv
│   ├── gsea_results.csv
│   ├── methods.md
│   └── results.md
└── figures/
    ├── umap_celltypes.pdf
    ├── marker_heatmap.pdf
    ├── marker_violin.pdf
    └── gsea_dotplot.pdf
```

---

## 🧠 Tip: Iterate and Re-run

Because sessions are stateful and saved, you can iterate cheaply:

```python
# Later — refine
session = ScienceSession.load("pbmc_analysis.pkl")

refined = session.analyze(
    task="Re-cluster only the T cells at higher resolution",
    specialist="scanpy_specialist",
    subset="cell_type == 'T cell'",
    resolution=1.0,
)
```

---

## 🚀 Variations

### Atlas-scale integration (multiple samples)

```python
session.load_data("run1.h5ad", name="run1")
session.load_data("run2.h5ad", name="run2")

session.analyze(
    task="Integrate samples with Harmony",
    specialist="data_integrator",
    batch_key="sample",
)
```

### Use Seurat instead of Scanpy

```python
clustered = session.analyze(
    task="Normalize, find HVG, cluster with Louvain",
    specialist="seurat_specialist",
    normalization_method="LogNormalize",
    resolution=0.5,
)
```

### RNA velocity

```python
velocity = session.analyze(
    task="Compute RNA velocity on the clustered object",
    specialist="scanpy_specialist",
    use_skill="scvelo",
)
```

---

## ⚠️ Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Doublets retained as a "new cell type" | Lower `max_genes`, or run `scrublet` explicitly |
| Clusters driven by cell cycle | Regress out `S_score`/`G2M_score` in normalize step |
| Over-clustering (resolution too high) | Drop to 0.3–0.5 for first pass; iterate up |
| Markers all mitochondrial/ribosomal | Filter these gene classes before clustering |
| Annotations don't make sense | Check the markers upstream; annotation quality depends on clustering quality |

---

## ➡️ Next Tutorial

**[Publication Figures →](publication-figures.md)**
