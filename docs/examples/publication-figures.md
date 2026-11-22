# Example: Publication Figures

Compose a multi-panel, journal-formatted figure from analysis results —
the kind of figure that goes straight into a submission.

**Agents used:** `layout_composer` → `matplotlib_stylist` →
`annotation_specialist` → `publication_formatter`

## Workflow

```python
from openscience import ScienceSession

session = ScienceSession()
session.load_data("data/pbmc_10k.h5ad", format="anndata")

# Run (or reload) the analyses that produce source figures
analysis = session.analyze(
    task="Cluster and identify cell types",
    specialist="scanpy_specialist",
)
de = session.analyze(
    task="Differential expression between CD14 and FCGR3A monocytes",
    specialist="deseq2_specialist",
)

# 1. Generate the individual panels
umap = session.visualize(analysis, type="umap", color="cell_type")
dotplot = session.visualize(analysis, type="dotplot")
volcano = session.visualize(de, type="volcano")

# 2. Compose a multi-panel figure with shared captions
figure = session.compose_figure(
    panels=[umap, dotplot, volcano],
    layout="1x3",
    panel_labels=["A", "B", "C"],
    specialist="layout_composer",
)

# 3. Style: consistent fonts, accessible palette
styled = session.style_figure(
    figure,
    font="Arial",
    palette="colorblind-safe",
    specialist="matplotlib_stylist",
)

# 4. Annotate: scale bars, significance stars, panel titles
annotated = session.annotate_figure(
    styled,
    titles=["Cell types", "Marker expression", "DE: CD14 vs FCGR3A"],
    specialist="annotation_specialist",
)

# 5. Format to journal specs (width, DPI, file type)
final = session.format_figure(
    annotated,
    journal="Nature",
    width_mm=180,
    dpi=300,
    output="figures/figure_3.pdf",
    specialist="publication_formatter",
)
```

## Expected Artifacts

| Artifact | Description |
|----------|-------------|
| `figures/panels/umap.pdf` | Source panels (with provenance) |
| `figures/figure_3.pdf` | Composed, journal-formatted figure |
| `figures/figure_3.svg` | Vector version for post-editing |
| `figures/figure_3.spec.json` | Reproducible spec: fonts, palette, layout |

## Tips

- Always export SVG alongside PDF so vector edits remain possible.
- The `color_palette_designer` agent checks palettes for color-vision
  accessibility before you commit to them.
- Journal presets live with the `publication_formatter` agent — see the
  [Agent Catalog](../agents.md#figure-generation-agents-15).
