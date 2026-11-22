---
layout: default
title: Examples
nav_order: 14
has_children: true
description: "Step-by-step tutorial examples"
---

# Tutorial Examples

Complete, real-world workflows showing how openScience's agents chain together.

## Available Tutorials

| Tutorial | Workflow | Time |
|----------|----------|------|
| [Systematic Literature Review](literature-review.md) | Search → Screen → Meta-analyze → Write | ~30 min |
| [Single-Cell RNA-seq Analysis](single-cell-analysis.md) | QC → Cluster → Annotate → Visualize | ~20 min |
| [Bulk RNA-seq Analysis](rnaseq-analysis.md) | DESeq2 → GSEA → Figures | ~15 min |
| [Publication Figures](publication-figures.md) | Panels → Compose → Verify → Export | ~10 min |

All examples follow the same pattern:

```python
from openscience import ScienceSession

session = ScienceSession()
session.load_data("<your data>")
result = session.analyze("<task description>")
session.visualize(result, output="figures/")
print(session.write_methods(result))
```

> Every figure and manuscript section produced by these examples carries a full provenance graph — see [API Reference](../api.md).

## Before You Start

1. [Install openScience](../getting-started.md)
2. [Quickstart tutorial](../quickstart.md)
3. Configure LLM key (for auto-routing and writing agents)

All tutorials assume your `openscience.yaml` is set up.

## Need Help?

- [Troubleshooting](../troubleshooting.md)
- [FAQ](../faq.md)
- [GitHub Issues](https://github.com/YakinRubaiat/openScience/issues)
