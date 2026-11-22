---
layout: default
title: "Example: Publication Figures"
parent: Examples
nav_order: 3
description: "Multi-panel, journal-formatted figures with openScience"
---

# Publication Figures

Build a multi-panel, journal-ready figure from analysis outputs — with correct fonts, colors, lettered panels, and export at print resolution.

---

## 🎯 The Goal

Turn three analysis outputs into a **Nature-format composite figure** with:

- UMAP (panel a)
- Marker heatmap (panel b)
- GSEA dotplot (panel c)
- Stylistic consistency (fonts, palette, panel letters)
- Vector output (PDF/SVG) at final print size

**Time**: ~10 minutes

---

## 📋 Prerequisites

- Results from [Single-Cell Analysis](single-cell-analysis.md) (or any three figures)
- openScience with the `viz` extras for interactive plots (optional)

---

## ✅ Step keys: Plan the Layout

Journal figures are typically **178 mm wide (two-column)** with panels arranged in a grid.

```python
from openscience import ScienceSession

session = ScienceSession(project_dir=".")

# Load pre-computed results
session.load_data("data/processed/adata_annotated.h5ad", format="anndata", name="pbmc")
markers = session.load_data("results/markers_per_cluster.csv", format="csv", name="markers")
gsea = session.load_data("results/gsea_results.csv", format="csv", name="gsea")
```

**Layout plan** (178 × 160 mm):

```
┌─────────────────────────┬────────────┐
│                         │            │
│   a) UMAP               │ b) Heatmap │
│   (100 × 110 mm)        │ (78 × 110) │
│                         │            │
├─────────────────────────┴────────────┤
│                                      │
│   c) GSEA dotplot (178 × 50 mm)      │
│                                      │
└──────────────────────────────────────┘
```

---

## ✅ Step 1 — Build individual panels

```python
# Panel a — UMAP
umap = session.analyze(
    task="UMAP colored by cell_type, large points, no frame, legend on data",
    specialist="publication_formatter",
    style="nature",                  # sets fonts (Arial 7), linewidths
    data=session._data["pbmc"],
    panel_label="a",
)

# Panel b — Heatmap of top 10 markers
heat = session.analyze(
    task="Heatmap of top 10 markers per cell type, dendrogram on genes only",
    specialist="seaborn_stylist",
    data=session._data["markers"],
    n_genes=10,
    cmap="RdBu_r",
    panel_label="b",
)

# Panel c — GSEA dotplot
gsea_plot = session.analyze(
    task="Dotplot of top 5 enriched pathways per cell type, size=NES, color=FDR",
    specialist="publication_formatter",
    data=session._data["gsea"],
    top_n=5,
    panel_label="c",
)
```

`style="nature"` applies:

- Font: Arial, 7 pt (base size)
- Line width: 0.5 pt
- Panel label: bold, **not** followed by a period
- Palette: colorblind-safe (`colorblind` from seaborn)

Other built-in styles: `science`, `cell`, `plos`, `nejm`.

---

## ✅ Step 2 — Compose the multi-panel figure

```python
composite = session.analyze(
    task="Compose panels into 178 mm wide figure: a+b top row, c full-width bottom row",
    specialist="layout_composer",
    panels=[umap, heat, gsea_plot],
    layout=[
        ["a", "b"],
        ["c", "c"],
    ],
    width_mm=178,
    height_mm=160,
    panel_label_fontsize=8,
    column_ratios=[100, 78],
    row_ratios=[110, 50],
    hspace_mm=4,
    wspace_mm=8,
)

session.analyze(
    task="Export composite as PDF and SVG",
    specialist="vector_graphics_editor",
    figure=composite,
    outputs=["figures/fig1.pdf", "figures/fig1.svg"],
    raster_dpi=600,          # embedded raster panels at 600 dpi
    fonts_embed=True,        # embed fonts for portability
)
```

The `layout_composer` agent:

- Places panels on a millimeter grid
- Auto-adds panel letters
- Aligns y labels and titles across panels
- Reruns `tight_layout` with mm units

---

## ✅ Step 3 — Verify accessibility

```python
# Check colorblind-friendliness
check = session.analyze(
    task="Audit figure for accessibility: colorblind simulation, minimum font size",
    specialist="data_viz_consultant",
    figure=composite,
)

print(check.data["report"])
# 'UMAP palette is colorblind-safe'
# 'Min font size: 7 pt (OK for Nature)'
# 'Contrast ratio on heatmap: 4.6:1 (OK)'
```

If the report flags issues, the `color_palette_designer` agent proposes alternatives:

```python
palette = session.analyze(
    task="Propose a colorblind-safe palette for 6 cell types",
    specialist="color_palette_designer",
    n_colors=6,
    style="categorical",
)
```

---

## ✅ Step 4 — Interactive variant (optional)

For the online version of the paper, generate an interactive companion:

```python
interactive = session.analyze(
    task="Interactive UMAP: hover for cell metadata, toggle gene expression overlay",
    specialist="interactive_dashboard",
    data=session._data["pbmc"],
    port=8050,
)
```

Visit `http://localhost:8050` to explore.

---

## ✅ Step 5 — Captions and source data

```python
# Caption
caption = session.analyze(
    task=(
        "Write figure caption: one sentence title, then one sentence per panel. "
        "Include n (cells), statistical tests, software versions."
    ),
    specialist="abstract_writer",   # caption style is similar
    figure=composite,
)
with open("figures/fig1_caption.txt", "w") as f:
    f.write(caption.data["caption"])

# Source data (required by many journals)
session.analyze(
    task="Export source data workbook for all panels",
    specialist="dataset_descriptor",
    outputs=["figures/source_data_fig1.xlsx"],
    include_provenance=True,
)
```

---

## 📂 Output Bundle

```
figures/
├── fig1.pdf                    ← print submission
├── fig1.svg                    ← vector for editing
├── fig1_caption.txt
├── source_data_fig1.xlsx       ← Nature's Source Data requirement
├── umap_panel.a.pdf            ← individual panels (kept)
├── heatmap_panel.b.pdf
└── gsea_dotplot_panel.c.pdf
```

---

## 🎨 Style Guide: Journal Differences

| Element | Nature | Science | Cell | PLOS |
|---------|--------|---------|------|------|
| Font | Arial | Helvetica | Arial | Arial |
| Min size | 5 pt | 5 pt | 6 pt | 6 pt |
| Panel labels | a, b, c | (A), (B) | A, B | A, B |
| Line width | 0.5–1 pt | 0.5–1 pt | 0.5–1.5 pt | 0.5–1 pt |
| Max width | 178 mm | 174 mm | 174 mm | 180 mm |

Switch styles via `style="science"`, etc.

---

## ⚠️ Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Text truncated in the PDF | Pass `bbox_inches="tight"` during export |
| Fonts not embedded | `fonts_embed=True`; verify with `pdffonts fig1.pdf` |
| Different font sizes across panels | Compose with `layout_composer` — it normalizes font scales |
| Raster panel looks blurry | Pass `raster_dpi=600` during export |
| Colors shift between screen and print | Export to PDF with CMYK profile: `color_profile="cmyk"` |
| Figure too heavy for editorial system | Export PNG at 300 dpi as a fallback |

---

## 🚀 Variations

### Add a schematic (biological illustration)

```python
schematic = session.analyze(
    task="Schematic of the experimental design: cells → editing → transplantation",
    specialist="schematic_illustrator",
)
```

### 3D structure inset

```python
structure = session.analyze(
    task="Render HBB protein with mutation highlighted",
    specialist="3d_visualizer",
    pdb_id="1A00",
    style="cartoon",
)
```

### Animated supplement

```python
session.analyze(
    task="Animate UMAP colored by pseudotime",
    specialist="animation_generator",
    frames=60,
    output="figures/supplement_movie.mp4",
)
```

---

## ➡️ Wrap-Up

You now have:

- A composite, journal-spec figure
- Source data workbook
- Accessibility-checked palette
- Reproducible caption

Return to the [tutorials hub](../index.md#-tutorial-examples) for more workflows.
