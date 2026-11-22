# openScience Documentation

## Table of Contents

1. [Getting Started](getting-started.md)
2. [Architecture](architecture.md)
3. [Agent Catalog](agents.md)
4. [API Reference](api.md)
5. [Configuration](configuration.md)
6. [Security](security.md)
7. [Contributing](contributing.md)

## Quick Links

- [Installation](#installation)
- [First Analysis](#first-analysis)
- [Agent Overview](#agent-overview)

## Installation

```bash
pip install openscience
```

## First Analysis

```python
from openscience import ScienceSession

session = ScienceSession()
session.load_data("data/experiment.h5ad")
result = session.analyze("Quality control and clustering")
```

## Agent Overview

openScience includes 100 specialized agents organized into six categories:

| Category | Count | Examples |
|----------|-------|----------|
| Literature Review | 15 | PubMed search, citation analysis, systematic review |
| Experiment Planning | 15 | Power analysis, protocol optimization, cost estimation |
| Data Management | 15 | Import, validation, batch correction, versioning |
| Data Analysis | 20 | QC, RNA-seq, single-cell, proteomics, ML |
| Figure Generation | 15 | Publication figures, interactive dashboards, 3D viz |
| Scientific Writing | 20 | Abstracts, methods, grants, presentations |

See [Agent Catalog](agents.md) for complete documentation.
