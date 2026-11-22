---
layout: default
title: "Example: Systematic Literature Review"
parent: Examples
nav_order: 1
description: "PRISMA-compliant systematic review workflow with openScience"
---

# Systematic Literature Review

A complete walkthrough: from a research question to a PRISMA-compliant review with forest plots.

---

## 🎯 The Goal

> *"What is the efficacy of CRISPR-Cas9 base editing for treating sickle cell disease?"*

By the end of this tutorial you will have:

- A documented search strategy across PubMed, bioRxiv, and ClinicalTrials.gov
- A deduplicated corpus with screening decisions
- PRISMA flow diagram
- Meta-analysis with forest plots
- Draft introduction section

**Time**: ~30 minutes (plus overnight for full text retrieval if you enable it)

---

## 📋 Prerequisites

- openScience installed
- LLM key configured (for summarization and synthesis)
- Optional: NCBI API key for higher PubMed rate limits

---

## ✅ Step 1 — Define the search strategy

Create `lit_review.py`:

```python
from openscience import ScienceSession

session = ScienceSession(project_dir="./sickle_cell_review")

# 1. Systematic search across databases
print("📚 Searching PubMed...")
pubmed_results = session.analyze(
    task=(
        "Search PubMed for CRISPR-Cas9 base editing in sickle cell disease. "
        "Use MeSH terms: 'sickle cell disease', 'CRISPR', 'base editing'. "
        "Filter: clinical trials OR preclinical studies. Date range: 2016–2025."
    ),
    specialist="pubmed_search",
    date_range=("2016-01-01", "2025-12-31"),
    retmax=500,
)

print("📄 Searching bioRxiv for recent preprints...")
preprints = session.analyze(
    task="Search bioRxiv for 'base editing sickle cell'",
    specialist="biorxiv_monitor",
    days_back=365*5,
)

print("🏥 Searching ClinicalTrials.gov...")
trials = session.analyze(
    task="Find clinical trials for base editing in sickle cell disease",
    specialist="clinical_trials",
    condition="Sickle Cell Disease",
    intervention="base editing",
)
```

**What just happened?**

- `pubmed_search` queried NCBI E-utilities with proper MeSH terms and rate limiting
- `biorxiv_monitor` polled the bioRxiv API
- `clinical_trials` hit ClinicalTrials.gov v2 API
- All went through the connector framework with caching

---

## ✅ Step 2 — Systematic screening

```python
# 2. PRISMA-compliant screening
print("🔍 Screening results...")
screening = session.analyze(
    task=(
        "Apply PRISMA workflow: "
        "1) Deduplicate by DOI/PMID. "
        "2) Title/abstract screen for relevance. "
        "3) Full-text eligibility check. "
        "Inclusion: human SCD models or patients, base editing intervention, "
        "functional outcome measured. "
        "Exclusion: reviews, editorials, non-English, no outcome data."
    ),
    specialist="systematic_review",
    corpora=[pubmed_results, preprints, trials],
)

print(f"Included: {screening.data['included_count']}")
print(f"Excluded: {screening.data['excluded_count']}")
print(f"Reasons: {screening.data['exclusion_reasons']}")

# PRISMA flow diagram
session.visualize(
    screening,
    type="prisma",
    output="figures/prisma_flow.pdf",
)
```

The `systematic_review` agent:

- Deduplicates via DOI/PMID + title fuzzy matching
- Screens title/abstract with explicit criteria
- Documents every exclusion reason (required for PRISMA)
- Generates the flow diagram automatically

---

## ✅ Step 3 — Extract data and analyze

```python
# 3. Extract effect sizes
print("📊 Extracting outcome data...")
effects = session.analyze(
    task=(
        "Extract base editing efficacy from included studies: "
        "editing efficiency (%), HbF induction (%), off-target rate, "
        "cell viability. Note sample sizes and confidence intervals."
    ),
    specialist="meta_analysis",
    studies=screening.data["included"],
)

# 4. Meta-analysis + forest plot
print("📈 Computing pooled estimates...")
meta = session.analyze(
    task=(
        "Random-effects meta-analysis on editing efficiency. "
        "Report pooled estimate, 95% CI, I² heterogeneity, "
        "and generate forest plot."
    ),
    specialist="meta_analysis",
    effect_data=effects,
    method="random_effects",
    heterogeneity_test="I2",
)

session.visualize(
    meta,
    type="forest",
    output="figures/forest_plot.pdf",
    style="publication",
)
```

---

## ✅ Step 4 — Identify gaps and write

```python
# 5. Research gaps
gaps = session.analyze(
    task="Identify understudied aspects of base editing for SCD in this corpus",
    specialist="research_gap_analyzer",
    corpus=screening.data["included"],
)
print(gaps.data["summary"])

# 6. Draft introduction
intro = session.write_methods(
    screening,
    style="nature",
    section="introduction",
)
with open("results/introduction.md", "w") as f:
    f.write(intro)

# 7. Save the session for later
session.save("checkpoint.pkl")
```

---

## 📂 Resulting File Tree

```
sickle_cell_review/
├── openscience.yaml
├── checkpoint.pkl
├── data/
│   ├── raw/                      # search results (immutable)
│   └── processed/                # deduplicated corpus
├── results/
│   ├── included_studies.csv
│   ├── exclusion_log.md
│   ├── meta_analysis.json
│   └── introduction.md
└── figures/
    ├── prisma_flow.pdf
    └── forest_plot.pdf
```

---

## 🧠 Tips

### Customize inclusion criteria

Be explicit and testable:

```
Inclusion:
- Primary research (not reviews)
- Reports editing efficiency as %
- SCD patient cells or SCD mouse model
- Published in English

Exclusion:
- n < 3 replicates
- No SCD-relevant readout
- Editorial, commentary, review
```

### Multiple screeners

Human verification matters. Export for review:

```python
screening.data["excluded_df"].to_csv("results/for_human_review.csv")
```

### Audit the decisions

Each screening decision has provenance. Ask:

```python
session.ask("Why was study NCT03164135 excluded?")
```

### Sensitivity analysis

Rerun with different thresholds:

```python
meta_strict = session.analyze(
    task="Sensitivity analysis: only studies with n>=5 replicates",
    specialist="meta_analysis",
    effect_data=effects,
    min_replicates=5,
)
```

---

## ⚠️ Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| PubMed rate-limiting | Set `NCBI_API_KEY`; respect `rate_limit: 10` |
| bioRxiv duplicates of PubMed papers | The dedup stage handles this — don't pre-filter |
| Missing MeSH terms in query | Use the `pubmed_search` agent's query expansion; don't write Boolean strings by hand |
| Forgotten exclusion reasons | Always pass `require_reason=True` to `systematic_review` |
| Cherry-picked effect sizes | Predefine the outcome measures before screening |

---

## 🚀 Variations

- **Scoping review**: drop meta-analysis, keep gap analysis
- **Living review**: schedule `biorxiv_monitor` weekly and rerun incrementally
- **Umbrella review**: use `openalex` for citation graph topology across reviews

---

## ➡️ Next Tutorial

**[Single-Cell RNA-seq Analysis →](single-cell-analysis.md)**
