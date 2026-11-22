# Frequently Asked Questions

## General

### What is openScience?

openScience is an open-source AI workbench for scientific research. It
combines 100 specialist agents, ~150 curated scientific skills, and 60+
database connectors inside a deny-by-default sandbox, so researchers can go
from question to reproducible artifact with full provenance.

### How does it relate to Claude Science?

openScience is inspired by [Claude Science](https://claude.com/product/claude-science)
and aims to provide comparable agentic research capabilities as open-source
software you can run and audit yourself.

### What does it cost?

The software is MIT-licensed and free. You pay only for your own compute
and any third-party API fees (e.g., cloud GPUs).

### Which domains are supported?

Genomics, single-cell, proteomics, metabolomics, drug discovery, and general
ML — 20 data-analysis agents cover RNA-seq, ChIP-seq, ATAC-seq, methylation,
metagenomics, flow cytometry, imaging, and more. See the
[Agent Catalog](agents.md).

## Installation

### Docker or local Python?

Docker Compose (`docker-compose up -d`) is the recommended path — it runs the
full stack (UI, API, workers, PostgreSQL, Redis) reproducibly. Local Python
installs are for development. See [Getting Started](getting-started.md).

### What are the system requirements?

macOS 13+ or Linux, Python 3.10+, 16 GB RAM, 50 GB disk. Some skills
(AlphaFold2, GROMACS) benefit from GPUs or HPC access, which you can attach
through the [compute backend router](architecture.md).

### Do I need a GPU?

No — most agents run fine on CPU. Deep-learning and molecular-dynamics
skills can be dispatched to cloud GPUs or SLURM clusters when available.

## Usage

### How do the 100 agents work together?

You describe a task in natural language; the orchestrator plans the workflow
and delegates to specialist agents (see [Architecture](architecture.md)). You
never have to pick agents manually, though you can pin one with the
`specialist` parameter.

### Is my data sent anywhere?

No — not by default. Network egress is deny-by-default; agents can only reach
database connectors (PubMed, PDB, …) with approved destinations, and every
request is logged.

### Can I reproduce an analysis later?

Yes. Every artifact carries its provenance graph — code, data versions, and
parameters — and complete pipelines can be exported. See
[API Reference](api.md#artifacts).

### How do I add my own tools?

Skills are registered through the skill registry, and new specialist agents
declared in `src/openscience/agents/`. See [Contributing](contributing.md).

## Security

### Where do my API keys live?

In the OS keyring, set with `openscience credentials set <service>`. Never in
`.env` or source. See [Security](security.md).

### What is the human-approval broker?

A gate that pauses privileged actions — arbitrary code execution, new network
destinations, deletions — until a human approves them. It's the core of the
sandbox model described in [Security](security.md).

### How do I report a vulnerability?

Privately, per the disclosure process in [Security](security.md) — never in a
public issue.

## Troubleshooting

### Where are logs?

`docker-compose logs -f <service>` (Docker) or the `LOG_LEVEL`-controlled
application logs (local install). See [Troubleshooting](troubleshooting.md).

### The docs server says port 8000 is in use

That's the REST API's port. Serve docs on another port:
`mkdocs serve --dev-addr 127.0.0.1:8001`. See
[Troubleshooting](troubleshooting.md#docs).
