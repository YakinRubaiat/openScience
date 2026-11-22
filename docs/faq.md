---
layout: default
title: FAQ
nav_order: 13
description: "Frequently asked questions about openScience"
---

# Frequently Asked Questions

---

## General

### What is openScience?

openScience is an open-source AI workbench for scientific research. It provides **100 specialized agents** across literature review, experiment planning, data management, analysis, visualization, and scientific writing — all with full provenance tracking and a security-first design.

### How is it different from just using ChatGPT/Claude directly?

| Aspect | Direct LLM | openScience |
|--------|-----------|-------------|
| Tool use | Limited plugins | 150+ scientific tools |
| Reproducibility | Chat history only | Full provenance graphs |
| Compute scaling | Cloud-only | Local, HPC, cloud |
| Domain knowledge | General | Field-specific agents |
| Sandbox | Limited | OS-level, deny-by-default |
| Privacy | Data sent to provider | Local-first, your keys |

### Is it free?

The software is MIT-licensed and free. You pay only for:
- The LLM API you choose (OpenAI, Anthropic, or a local model)
- Your own compute (free if local)

### Can I use it without any LLM keys?

Yes — most agents work without an LLM, but natural-language task routing and AI-assisted writing need one. You can specify agents explicitly (`specialist="scanpy_specialist"`) to skip the LLM router entirely.

---

## Installation

### Docker or local install — which should I pick?

- **Docker** if you want the full stack with PostgreSQL/Redis and don't want dependency headaches.
- **Local** if you're developing, need custom system tools (e.g., licensed Cell Ranger), or work in a restricted environment.

Both run the same code.

### Does it work on Windows?

We target macOS and Linux. Windows support via WSL2 works well; native Windows isn't officially supported.

### What Python versions are supported?

Python **3.10+**. We develop against 3.12.

### Do I need a GPU?

No for the vast majority of agents. A GPU helps for `deep_learning_specialist`, `3d_visualizer` on large structures, and large-scale training jobs.

---

## Agents

### How do I know which agent to use?

1. Browse the [Agent Catalog](agents.md)
2. Let the orchestrator auto-route (`specialist=None`)
3. Use `session.ask("Which agent should I use for X?")` — though this uses an LLM

### An agent isn't doing what I expected — now what?

1. Check the agent's entry in the catalog for expected inputs/outputs
2. Examine the task description you gave — vague descriptions get vague results
3. Check logs in `logs/openscience.log`
4. Try a specialist agent explicitly rather than auto-routing

### Can I run multiple agents in parallel?

Yes:

```python
import asyncio

async def run_all():
    results = await asyncio.gather(
        session.analyze("QC", specialist="qc_analyzer"),
        session.analyze("Batch correction", specialist="batch_corrector"),
    )
    return results
```

Set `agents.parallel_workers` in `openscience.yaml` to control concurrency.

### How do I add my own agent?

See [Contributing — Adding a New Agent](contributing.md#adding-a-new-agent).

---

## Data and Privacy

### Where does my data go?

Nowhere by default. openScience is **local-first**:

- Data stays on your machine (or your cluster)
- Only task descriptions and metadata leave — and only to the LLM you configured
- Database connectors fetch public data; they don't send your data

### Can I use HIPAA/PHI data?

The sandbox and encryption support work with sensitive data, but you are responsible for:

- Signing a BAA with your LLM provider (or using local models)
- Institutional approval for your specific workload
- Configuring the sandbox appropriately

The `privacy_guardian` agent detects and masks PII/PHI as a first line of defense.

### How is `data/raw` protected?

The sandbox mounts it read-only. Agents can't modify source data; they write derivatives to `data/processed/`.

---

## Compute

### Can I dispatch jobs to my university HPC?

Yes — configure the SLURM backend:

```yaml
compute:
  default: slurm
  backends:
    slurm:
      partition: main
      account: mylab
```

Details in [Configuration](configuration.md#compute-backends).

### How much memory do I need?

Rule of thumb:

| Workload | RAM |
|----------|-----|
| Single-cell, 10k cells | 8–16 GB |
| Single-cell, 100k cells | 32 GB |
| Atlas-scale, 1M+ cells | 64+ GB or HPC |
| Bulk RNA-seq | 8–16 GB |
| Deep learning | GPU with 16+ GB VRAM |

### Can I run on AWS/GCP/Azure?

Yes, via the `cloud` backend or by deploying Docker images on a VM. See [Docker Deployment](docker.md).

---

## Output and Reproducibility

### Where are results stored?

- **In memory**: `session._results`
- **On disk**: `results/` and `figures/` under your `project_dir`
- **Persisted sessions**: `session.save(path)` → `ScienceSession.load(path)`

### How do I reproduce an analysis later?

Every result records:

- Tool versions (from the skill registry)
- Parameters used
- Input checksums
- Timestamp and agent identity

Export with:

```python
session.save("analysis.pkl")
```

The pickle + your `openscience.yaml` + your raw data fully recreates the workflow.

### Can I version control the outputs?

Yes. We recommend:

- Track `openscience.yaml` in git
- Track small results (tables, methods text) in git
- Track large artifacts with [DVC](https://dvc.org/) or git-annex (use the `version_controller` agent)

---

## Errors and Debugging

### Something broke — where do I look first?

1. `logs/openscience.log`
2. `openscience config` — verify the merged configuration
3. The [Troubleshooting guide](troubleshooting.md)
4. [GitHub issues](https://github.com/YakinRubaiat/openScience/issues)

### The LLM picked the wrong agent — can I override it?

Always. Specify `specialist="<name>"` explicitly:

```python
session.analyze("QC",
                specialist="scanpy_specialist",   # ← explicit
                min_genes=200)
```

Or lower `agents.auto_route` and `agents.confidence_threshold` in `openscience.yaml`.

### My analysis is taking forever — can I speed it up?

- Profile with `logging.level: DEBUG`
- Use a faster compute backend
- Subsample first for iteration
- Cache connector results

---

## Contributing

### I have an idea for an agent — where do I start?

1. Check the [catalog](agents.md) to confirm it doesn't exist
2. Open a GitHub discussion to gather feedback
3. Follow the guide in [Contributing](contributing.md#adding-a-new-agent)

### My PR has merge conflicts — what now?

```bash
git fetch upstream
git rebase upstream/main
# resolve conflicts
git push --force-with-lease
```

Or ask in the PR — reviewers are happy to help.

---

## License and Citation

### Can I use openScience in my company / lab?

Yes — it's MIT-licensed.

### How do I cite openScience?

```bibtex
@software{openscience2025,
  title = {openScience: An Open-Source AI Workbench for Scientific Research},
  author = {openScience Contributors},
  year = {2025},
  url = {https://github.com/YakinRubaiat/openScience},
  version = {0.1.0}
}
```

---

## ➡️ Still Have a Question?

- [GitHub Discussions](https://github.com/YakinRubaiat/openScience/discussions)
- [Open an issue](https://github.com/YakinRubaiat/openScience/issues)
- [Troubleshooting guide](troubleshooting.md)
