---
layout: default
title: 5-Minute Quickstart
nav_order: 3
description: "Run your first analysis in under 5 minutes"
---

# 5-Minute Quickstart

In this tutorial you'll analyze a single-cell RNA-seq dataset end-to-end: load data, run quality control and clustering, generate a UMAP figure, and draft a methods section.

**Time:** ~5 minutes (not counting the one-time data download)

---

## What You'll Build

```text
Input:  pbmc_10k.h5ad  (10k PBMCs from 10x Genomics)
   ↓
QC + normalization + clustering          →  results/
   ↓
UMAP visualization (publication-ready)   →  figures/umap.pdf
   ↓
Methods section (Nature-style)           →  results/methods.md
```

---

## Prerequisites

- openScience installed ([installation guide](getting-started.md))
- ~250 MB free disk space for the sample dataset

You can follow along with the **Python API**, the **CLI**, or the **REST API**. Pick your favorite.

---

## Step 1 — Get the sample data

```bash
mkdir -p data/raw

curl -L -o data/raw/pbmc_10k.h5ad \
  https://cf.10xgenomics.com/samples/cell-exp/3.0.0/pbmc_10k_v3/pbmc_10k_v3_filtered_feature_bc_matrix.h5ad
```

> **What is this?** Single-cell RNA-seq from ~10,000 human peripheral blood mononuclear cells (PBMCs), preprocessed by Cell Ranger into an `AnnData` object.

---

## Step 2 — Run the analysis (Python API)

Create `quickstart.py`:

```python
from openscience import ScienceSession

# 1. Start a session in the current project directory
session = ScienceSession(project_dir=".")

# 2. Load the dataset
print("🔬 Loading data...")
session.load_data("data/raw/pbmc_10k.h5ad", format="anndata", name="pbmc")

# 3. QC + normalization + clustering with the scanpy specialist
print("📊 Running QC and clustering...")
result = session.analyze(
    task="Perform QC filtering, normalization, and clustering",
    specialist="scanpy_specialist",
    min_genes=200,
    min_cells=3,
    max_pct_mito=20,
    n_neighbors=10,
    n_pcs=40,
    resolution=0.5,
)

# 4. Make a publication-quality UMAP
print("📈 Generating UMAP...")
session.visualize(
    result,
    type="umap",
    style="publication",
    output="figures/umap_clusters.pdf",
    color="leiden",
)

# 5. Draft the methods section
print("✍️  Writing methods...")
methods = session.write_methods(result, style="nature")
with open("results/methods.md", "w") as f:
    f.write(methods)

print("✅ Done! Check figures/ and results/")
```

Run it:

```bash
python quickstart.py
```

Expected output:

```text
🔬 Loading data...
📊 Running QC and clustering...
📈 Generating UMAP...
✍️  Writing methods...
✅ Done! Check figures/ and results/
```

---

## Alternative: Use the CLI

```bash
# Initialize the session and load data
openscience run load-data data/raw/pbmc_10k.h5ad --format anndata --name pbmc

# Run analysis
openscience run analyze \
  --task "QC filtering, normalization, and clustering" \
  --specialist scanpy_specialist \
  --param min_genes=200 --param min_cells=3 --param max_pct_mito=20

# Generate figure
openscience run visualize --type umap --style publication \
  --output figures/umap_clusters.pdf
```

---

## Alternative: Use the REST API

With `openscience start` (or `docker-compose up`) running:

```bash
# Load data
curl -X POST http://localhost:8080/api/session/load \
  -H "Content-Type: application/json" \
  -d '{"file_path": "data/raw/pbmc_10k.h5ad", "format": "anndata"}'

# Analyze
curl -X POST http://localhost:8080/api/session/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "task": "QC filtering, normalization, and clustering",
    "specialist": "scanpy_specialist"
  }'
```

Full endpoint reference: [API Documentation](api.md).

---

## Step 3 — Inspect the results

### numbers

Open the generated files:

```bash
open figures/umap_clusters.pdf     # your figure
cat results/methods.md             # your methods text
```

### Ask follow-up questions

Add to `quickstart.py`:

```python
answer = session.ask("How many cells passed QC, and how many clusters were found?")
print(answer)
```

The orchestrator inspects the stored result and replies with the numbers plus the parameters used.

---

## What Just Happened?

Behind the scenes, the orchestrator:

1. **Routed** `load_data` to the `data_ingestor` agent
2. **Routed** the analysis to `scanpy_specialist`, which called the `scanpy` skill:
   - Filtered cells with <200 genes; genes in <3 cells
   - Removed cells with >20% mitochondrial reads
   - Normalized (CP10k + log1p) and selected highly-variable genes
   - Built a kNN graph (10 neighbors, 40 PCs) and ran Leiden clustering (resolution 0.5)
3. **Routed** visualization to `publication_formatter`, which rendered the UMAP with journal-safe fonts and colors
4. **Routed** writing to `methods_writer`, which produced a methods paragraph including tool versions and parameters — pulled from the **provenance graph**

Every step is logged; nothing is a black box.

---

## Next Steps

### Try other specialists

Replace `scanpy_specialist` with:

| Specialist | Task |
|------------|------|
| `deseq2_specialist` | Bulk RNA-seq differential expression |
| `qc_analyzer` | QC report only (no clustering) |
| `ml_modeler` | Train a classifier on the clusters |
| `gsea_analyzer` | Pathway enrichment on cluster markers |

### Chain multiple agents

```python
# Find marker genes for each cluster
markers = session.analyze(
    "Find marker genes for each Leiden cluster",
    specialist="scanpy_specialist",
    method="wilcoxon",
)

# Run enrichment on top markers
enrichment = session.analyze(
    "GSEA on top 100 markers per cluster",
    specialist="gsea_analyzer",
    gene_sets="MSigDB_Hallmark",
)
```

### Explore tutorials

- **[Systematic Literature Review](examples/literature-review.md)**
- **[Publication Figures](examples/publication-figures.md)**
- **[Full Single-Cell Workflow](examples/single-cell-analysis.md)**

### Common pitfalls

- ⚠️ **Forgot `format="anndata"`**? `load_data` auto-detects `.h5ad`, but explicit is safer.
- ⚠️ **Out of memory?** PBMC 10k fits comfortably in 8 GB, but for larger atlases use `compute_backend="slurm"`.
- ⚠️ **Where are my figures?** Relative paths resolve against `project_dir`. Set it explicitly for scripts run from different directories.

---

## You Did It

You've run a complete agentic scientific workflow: ingest → analyze → visualize → document. Every result is reproducible and auditable.

**[Explore more examples →](examples/literature-review.md)**
