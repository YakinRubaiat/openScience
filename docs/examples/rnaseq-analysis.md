# Example: Bulk RNA-seq Analysis

Differential expression and pathway analysis from a count matrix, ending in a
publication-ready figure.

**Agents used:** `qc_analyzer` → `deseq2_specialist` → `gsea_analyzer` →
`publication_formatter`

## Workflow

```python
from openscience import ScienceSession

session = ScienceSession()

# 1. Load a count matrix (genes × samples) with sample metadata
session.load_data(
    "data/knockout_vs_control_counts.csv",
    format="count_matrix",
    metadata="data/sample_sheet.csv",
)

# 2. QC: library sizes, dispersion, PCA of replicates
qc = session.analyze(
    task="Run quality control on this count matrix",
    specialist="qc_analyzer",
)

# 3. Differential expression with DESeq2
de = session.analyze(
    task="Differential expression: knockout vs control",
    specialist="deseq2_specialist",
    prior=qc,
)

# 4. Pathway enrichment on significant genes
gsea = session.analyze(
    task="Gene set enrichment on significant genes (padj < 0.05)",
    specialist="gsea_analyzer",
    input_genes=de.significant_genes,
)

# 5. Publication figure: volcano plot with pathway annotations
figure = session.visualize(
    de,
    type="volcano",
    annotations=gsea.top_pathways,
    output="figures/volcano.pdf",
    specialist="publication_formatter",
)

# 6. Methods section for the manuscript
methods = session.write_methods([qc, de, gsea])
print(methods)
```

## Expected Artifacts

| Artifact | Description |
|----------|-------------|
| `reports/qc_report.html` | MultiQC-style QC summary |
| `tables/de_results.csv` | Full differential-expression table |
| `tables/gsea_results.csv` | Enriched gene sets |
| `figures/volcano.pdf` | Journal-formatted volcano plot |
| `manuscript/methods.md` | Draft methods section |

Each artifact's provenance can be fetched via
`/api/v1/artifacts/{id}/provenance` (see [API Reference](../api.md)).
