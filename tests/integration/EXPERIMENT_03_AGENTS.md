# Experiment 03 — Agent Execution Tests


**Date:** 2026-11-22

**Total runtime:** 0.01 s

**Tests run:** 10

**Passed:** 10/10


## Summary Table


| # | Test | Agent(s) | Time (s) | Status |
|---|------|----------|---------:|--------|
| 1 | Literature agent — pubmed_search | `pubmed_search` | 0.004 | ✅ PASS |
| 2 | Experiment agent — power_analysis | `power_analysis` | 0.000 | ✅ PASS |
| 3 | Data management agent — data_ingestor | `data_ingestor` | 0.000 | ✅ PASS |
| 4 | Analysis agent — qc_analyzer | `qc_analyzer` | 0.000 | ✅ PASS |
| 5 | Visualization agent — matplotlib_stylist | `matplotlib_stylist` | 0.000 | ✅ PASS |
| 6 | Writing agent — abstract_writer | `abstract_writer` | 0.000 | ✅ PASS |
| 7 | Review agent — security_reviewer | `security_reviewer` | 0.000 | ✅ PASS |
| 8 | Review agent — code_quality_reviewer | `code_quality_reviewer` | 0.000 | ✅ PASS |
| 9 | Agent chaining — pubmed_search → qc_analyzer → abstract_writer | `pubmed_search` → `qc_analyzer` → `abstract_writer` | 0.001 | ✅ PASS |
| 10 | Concurrent agent execution — 4 agents in parallel | `pubmed_search`, `qc_analyzer`, `matplotlib_stylist`, `code_quality_reviewer` | 0.001 | ✅ PASS |

---

## Test 1: Literature agent — pubmed_search


**Description:** Search PubMed for single-cell RNA-seq batch effect papers

**Parameters:**
```json
{
  "query": "single-cell RNA-seq batch effect correction",
  "max_results": 10
}
```

**Context:**
```json
{
  "user_id": "test-runner",
  "session": "exp03"
}
```

**Execution time:** 0.004 s

**Status:** ✅ **PASSED**

**Structure validation:**
- ✅ `is_result`: True
- ✅ `has_data`: True
- ✅ `has_metadata`: True
- ✅ `has_artifacts`: True

**Result summary:**
```json
{"papers": {"skill": "pubmed_api", "operation": "search", "status": "ok", "data": {"query": "single-cell RNA-seq batch effect correction", "max_results": 10}}, "count": 4, "query": "single-cell RNA-se
```

---

## Test 2: Experiment agent — power_analysis


**Description:** Compute required sample size for a two-group comparison

**Parameters:**
```json
{
  "effect_size": 0.5,
  "alpha": 0.05,
  "power": 0.8
}
```

**Context:**
```json
{
  "study": "pilot_trial",
  "session": "exp03"
}
```

**Execution time:** 0.000 s

**Status:** ✅ **PASSED**

**Structure validation:**
- ✅ `is_result`: True
- ✅ `has_data`: True
- ✅ `has_metadata`: True
- ✅ `has_artifacts`: True

**Result summary:**
```json
{"skill": "statsmodels", "operation": "power_analysis", "status": "ok", "data": {"effect_size": 0.5, "alpha": 0.05, "power": 0.8}}
```

---

## Test 3: Data management agent — data_ingestor


**Description:** Ingest a CSV expression matrix

**Parameters:**
```json
{
  "file_path": "/tmp/expression.csv",
  "format_hint": "csv"
}
```

**Context:**
```json
{
  "session": "exp03"
}
```

**Execution time:** 0.000 s

**Status:** ✅ **PASSED**

**Structure validation:**
- ✅ `is_result`: True
- ✅ `has_data`: True
- ✅ `has_metadata`: True
- ✅ `has_artifacts`: True

**Result summary:**
```json
{"data": {"skill": "bioio", "operation": "load", "status": "ok", "data": {"file_path": "/tmp/expression.csv", "format": "csv"}}, "format": "csv"}
```

---

## Test 4: Analysis agent — qc_analyzer


**Description:** Run QC analysis on single-cell dataset

**Parameters:**
```json
{
  "data_type": "single_cell"
}
```

**Context:**
```json
{
  "session": "exp03",
  "data": {
    "n_cells": 1200,
    "n_genes": 20000
  }
}
```

**Execution time:** 0.000 s

**Status:** ✅ **PASSED**

**Structure validation:**
- ✅ `is_result`: True
- ✅ `has_data`: True
- ✅ `has_metadata`: True
- ✅ `has_artifacts`: True

**Result summary:**
```json
{"skill": "scanpy", "operation": "qc_analysis", "status": "ok", "data": {"data": {"n_cells": 1200, "n_genes": 20000}}}
```

---

## Test 5: Visualization agent — matplotlib_stylist


**Description:** Apply Nature-journal style to a figure

**Parameters:**
```json
{
  "figure": "<matplotlib.figure.Figure mock>",
  "style": "nature"
}
```

**Context:**
```json
{
  "session": "exp03"
}
```

**Execution time:** 0.000 s

**Status:** ✅ **PASSED**

**Structure validation:**
- ✅ `is_result`: True
- ✅ `has_data`: True
- ✅ `has_metadata`: True
- ✅ `has_artifacts`: True

**Result summary:**
```json
{"figure": {"skill": "matplotlib", "operation": "apply_style", "status": "ok", "data": {"figure": "<matplotlib.figure.Figure mock>", "style": "nature"}}, "style": "nature"}
```

---

## Test 6: Writing agent — abstract_writer


**Description:** Draft an abstract for a single-cell study

**Parameters:**
```json
{
  "paper_content": "We applied scVI to integrate 1.2M PBMCs from 24 donors across 3 batches and identified a novel CD14+ monocyte subpopulation associated with severe COVID-19.",
  "target_journal": "Nature",
  "word_limit": 200
}
```

**Context:**
```json
{
  "session": "exp03"
}
```

**Execution time:** 0.000 s

**Status:** ✅ **PASSED**

**Structure validation:**
- ✅ `is_result`: True
- ✅ `has_data`: True
- ✅ `has_metadata`: True
- ✅ `has_artifacts`: True

**Result summary:**
```json
{"skill": "scientific_writing", "operation": "write_abstract", "status": "ok", "data": {"content": "We applied scVI to integrate 1.2M PBMCs from 24 donors across 3 batches and identified a novel CD14+
```

---

## Test 7: Review agent — security_reviewer


**Description:** Run security review on src/openscience

**Parameters:**
```json
{
  "target_path": "src/openscience/"
}
```

**Context:**
```json
{
  "session": "exp03"
}
```

**Execution time:** 0.000 s

**Status:** ✅ **PASSED**

**Structure validation:**
- ✅ `is_result`: True
- ✅ `has_data`: True
- ✅ `has_metadata`: True
- ✅ `has_artifacts`: True

**Result summary:**
```json
{"vulnerabilities": [], "recommendations": [], "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0}}
```

---

## Test 8: Review agent — code_quality_reviewer


**Description:** Run code-quality review on src/openscience

**Parameters:**
```json
{
  "target_path": "src/openscience/"
}
```

**Context:**
```json
{
  "session": "exp03"
}
```

**Execution time:** 0.000 s

**Status:** ✅ **PASSED**

**Structure validation:**
- ✅ `is_result`: True
- ✅ `has_data`: True
- ✅ `has_metadata`: True
- ✅ `has_artifacts`: True

**Result summary:**
```json
{"pylint_score": 0, "complexity_metrics": {"skill": "radon", "operation": "complexity", "status": "ok", "data": {"path": "src/openscience/"}}, "formatting_issues": [], "type_errors": [], "duplication"
```

---

## Test 9: Agent chaining — pubmed_search → qc_analyzer → abstract_writer


**Description:** Chain: search literature → run QC → draft abstract

**Execution time:** 0.001 s

**Status:** ✅ **PASSED**

**Structure validation:**
- ✅ `steps_completed`: True
- ✅ `all_results_valid`: True

**Steps:**
1. `pubmed_search` (0.000s)
   - Result summary: `{"papers": {"skill": "pubmed_api", "operation": "search", "status": "ok", "data": {"query": "scRNA-seq batch correction", "max_results": 5}}, "count": 4, "query": "scRNA-seq batch correction"}`
1. `qc_analyzer` (0.000s)
   - Result summary: `{"skill": "scanpy", "operation": "qc_analysis", "status": "ok", "data": {"data": {"n_cells": 5000, "n_genes": 18000}}}`
1. `abstract_writer` (0.000s)
   - Result summary: `{"skill": "scientific_writing", "operation": "write_abstract", "status": "ok", "data": {"content": "Results from integrated scRNA-seq analysis.", "journal": "Cell", "word_limit": 150}}`

---

## Test 10: Concurrent agent execution — 4 agents in parallel


**Description:** Run pubmed_search, qc_analyzer, matplotlib_stylist, code_quality_reviewer concurrently via asyncio.gather

**Execution time:** 0.001 s

**Status:** ✅ **PASSED**

**Structure validation:**
- ✅ `all_succeeded`: True
- ✅ `all_results_valid`: True
- ✅ `count`: 4

**Steps:**
1. `pubmed_search` (0.001s)
   - Result summary: `{"papers": {"skill": "pubmed_api", "operation": "search", "status": "ok", "data": {"query": "spatial transcriptomics", "max_results": 3}}, "count": 4, "query": "spatial transcriptomics"}`
1. `qc_analyzer` (0.001s)
   - Result summary: `{"skill": "scanpy", "operation": "qc_analysis", "status": "ok", "data": {"data": {"n_cells": 8000}}}`
1. `matplotlib_stylist` (0.001s)
   - Result summary: `{"figure": {"skill": "matplotlib", "operation": "apply_style", "status": "ok", "data": {"figure": "<fig>", "style": "nature"}}, "style": "nature"}`
1. `code_quality_reviewer` (0.001s)
   - Result summary: `{"pylint_score": 0, "complexity_metrics": {"skill": "radon", "operation": "complexity", "status": "ok", "data": {"path": "src/openscience/"}}, "formatting_issues": [], "type_errors": [], "duplication"`

---

## Notes


- Tests 1–8 exercise one agent each via `AgentOrchestrator.execute_agent().`
- Test 9 chains three agents sequentially, propagating each result's
  summary into the next agent's context.
- Test 10 runs four agents in parallel using `asyncio.gather()`.
- Skills are provided by the orchestrator's default stub executor,
  so return values are deterministic `{skill, operation, status, data}`
  envelopes. Real tool bindings can be installed by subclassing
  `AgentOrchestrator.execute_skill()`.
