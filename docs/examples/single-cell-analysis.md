# Example: Single-Cell Workflow

QC, clustering, and marker identification on 10x Genomics PBMC data.

**Agents used:** `qc_analyzer` → `scanpy_specialist` → `matplotlib_stylist` →
`methods_writer`

## Workflow

```python
from openscience import ScienceSession

session = ScienceSession()

# 1. Load 10x output (h5ad / filtered feature-barcode matrix)
session.load_data("data/pbmc_10k.h5ad", format="anndata")

# 2. QC: mitochondrial fraction, doublet screening, filtering
qc = session.analyze(
    task="Quality control: filter low-quality cells and genes",
    specialist="qc_analyzer",
)

# 3. Standard Scanpy pipeline: normalize, HVGs, PCA, neighbors,
#    UMAP, and Leiden clustering
analysis = session.analyze(
    task="Normalize, reduce dimensions, and cluster",
    specialist="scanpy_specialist",
    prior=qc,
)

# 4. Marker genes per cluster
markers = session.analyze(
    task="Rank marker genes for each cluster",
    specialist="scanpy_specialist",
    prior=analysis,
)

# 5. Figures: UMAP colored by cluster and top markers
session.visualize(
    analysis,
    type="umap",
    color="leiden",
    output="figures/umap_clusters.pdf",
    specialist="matplotlib_stylist",
)

session.visualize(
    markers,
    type="dotplot",
    output="figures/marker_dotplot.pdf",
)

# 6. Methods draft
methods = session.write_methods([qc, analysis, markers])
print(methods)
```

## Expected Artifacts

| Artifact | Description |
|----------|-------------|
| `data/processed.h5ad` | Filtered, annotated AnnData |
| `figures/umap_clusters.pdf` | UMAP with cluster labels |
| `figures/marker_dotplot.pdf` | Top markers per cluster |
| `manuscript/methods.md` | Methods section draft |

## Variations

- Use `specialist="seurat_specialist"` to run the equivalent Seurat pipeline
  in R via rpy2.
- Add `batch_corrector` before clustering when combining multiple donors
  (see [Agent Catalog](../agents.md)).
