---
layout: default
title: Home
nav_order: 1
description: "openScience documentation — an open-source AI workbench for scientific research"
permalink: /
---

# openScience Documentation

Welcome to the official documentation for **openScience**, an open-source AI workbench that brings agentic AI capabilities to computational biology, chemistry, neuroscience, and ML research.

openScience automates the toil between scientific questions and answers — handling database schemas, format conversions, and package interoperability — so researchers can focus on design decisions and interpretation.

---

## New here? Start with these

| Guide | Description |
|-------|-------------|
| [Getting Started](getting-started.md) | Install openScience with Docker or locally |
| [5-Minute Quickstart](quickstart.md) | Run your first analysis in under 5 minutes |
| [Configuration](configuration.md) | API keys, compute backends, and settings |

---

## Core Documentation

### Architecture and Design

- **[Architecture Deep-Dive](architecture.md)** — System design, components, and data flow
- **[Agent Catalog](agents.md)** — Complete reference for all 100 specialized agents
- **[API Reference](api.md)** — Python API, REST API, and CLI documentation

### Deployment and Operations

- **[Docker Deployment](docker.md)** — Containerized deployment from dev to production
- **[Development Setup](development.md)** — Local development environment

### Policies and Support

- **[Security Policies](security.md)** — Sandbox, biosecurity, credential management
- **[Troubleshooting](troubleshooting.md)** — Common issues and solutions
- **[FAQ](faq.md)** — Frequently asked questions

### Community

- **[Contributing Guide](contributing.md)** — How to contribute to openScience

---

## Navigate by Task

| I want to... | Start here |
|--------------|------------|
| Install openScience | [Getting Started](getting-started.md) |
| Run my first analysis | [Quickstart](quickstart.md) |
| Deploy with Docker | [Docker Guide](docker.md) |
| Find the right agent | [Agent Catalog](agents.md) |
| Automate a systematic review | [Literature Review Example](examples/literature-review.md) |
| Analyze single-cell data | [Single-Cell Example](examples/single-cell-analysis.md) |
| Make publication figures | [Publication Figures Example](examples/publication-figures.md) |
| Use the API | [API Reference](api.md) |
| Contribute an agent | [Contributing](contributing.md) |
| Fix an issue | [Troubleshooting](troubleshooting.md) |

---

## The Six Workflow Archetypes

openScience organizes its **100 specialized agents** into six categories covering the research lifecycle:

| Category | Agents | What it covers |
|----------|:------:|----------------|
| 📚 [Literature Review](agents.md#literature-review-agents-15) | 15 | Systematic search, summarization, synthesis, citation graphs |
| 🧪 [Experiment Planning](agents.md#experiment-planning-agents-15) | 15 | Power analysis, protocol design, feasibility, preregistration |
| 💾 [Data Management](agents.md#data-management-agents-15) | 15 | Ingestion, validation, batch correction, provenance |
| 📈 [Data Analysis](agents.md#data-analysis-agents-20) | 20 | QC, RNA-seq, single-cell, proteomics, ML |
| 📊 [Figure Generation](agents.md#figure-generation-agents-15) | 15 | Publication figures, interactive dashboards, 3D viz |
| ✍️ [Scientific Writing](agents.md#scientific-writing-agents-20) | 20 | Abstracts, methods, grants, reviewer responses |

---

## 60-Second Overview

### Python API

```python
from openscience import ScienceSession

session = ScienceSession()
session.load_data("data/pbmc_10k.h5ad", format="anndata")
result = session.analyze("Quality control and clustering")
figure = session.visualize(result, type="umap", output="figures/umap.pdf")
methods = session.write_methods(result)
```

### CLI

```bash
openscience init                    # Set up a new project
openscience agents                  # List all 100 agents
openscience start --port 8080       # Start the server
```

### Docker

```bash
docker-compose up -d
open http://localhost:8080
```

---

## Tutorial Examples

Step-by-step walkthroughs of complete workflows:

1. **[Systematic Literature Review](examples/literature-review.md)** — PRISMA-compliant review from search to PRISMA diagram
2. **[Single-Cell RNA-seq Analysis](examples/single-cell-analysis.md)** — End-to-end scRNA-seq from h5ad to cell-type annotation
3. **[Publication Figures](examples/publication-figures.md)** — Multi-panel, journal-formatted figures

---

## Getting Help

- **Something broken?** → [Troubleshooting](troubleshooting.md)
- **Quick question?** → [FAQ](faq.md)
- **Found a bug?** → [Open an issue](https://github.com/YakinRubaiat/openScience/issues)
- **Want to contribute?** → [Contributing Guide](contributing.md)

---

<div align="center">

**[Get Started →](getting-started.md)**

</div>
