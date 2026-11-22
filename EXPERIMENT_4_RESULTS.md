# EXPERIMENT 4 — Can openScience actually analyze real single-cell data?

**Date:** 2026-11-22 · **Agent runtime:** `openScience` HEAD · Python 3.13 (`.venv`)
**Dataset:** 10x Genomics PBMC 3K (`pbmc3k_filtered_gene_bc_matrices.tar.gz`, hg19)
**Verdict: PARTIAL SUCCESS — the agent framework works end-to-end, but every bioinformatics skill had to be implemented from scratch. There were *no real skills*: the orchestrator's `execute_skill` is a stub that echoes kwargs back.**

---

## Scientific results (real, reproduced the canonical PBMC3K analysis)

Processed 2,700 cells → 2,638 cells & 13,714 genes after QC filtering → 1,838 highly-variable genes → PCA(40) → kNN graph → UMAP → **Leiden clustering recovered 7 populations**, each identified by its canonical marker genes:

| Cluster | Cells | Top markers (Wilcoxon) | Canonical identity |
|---|---|---|---|
| 0 | 1,182 | RPS12, LDHB, RPS25, RPS27, RPS3 | CD4 T cells (naive, ribosome-high) |
| 1 | 341 | CD74, **CD79A**, HLA-DRA, CD79B | **B cells** |
| 2 | 487 | **LYZ, S100A9, S100A8**, TYROBP, FTL | **CD14+ monocytes** |
| 3 | 430 | **NKG7, CST7, GZMA**, B2M, CTSW | **NK cells** |
| 4 | 149 | LST1, **FCGR3A**, FCER1G, COTL1 | **FCGR3A+ (CD16) monocytes** |
| 5 | 36 | HLA-DPA1, HLA-DPB1, CD74 | **Dendritic cells** |
| 6 | 13 | **PF4, PPBP**, SDPR, GNG11 | **Megakaryocytes / platelets** |

QC metrics matched the reference analysis: median 817 genes/cell, median 2,197 UMIs/cell, median 2.03% mitochondrial content. This is the expected PBMC3K biology — **the pipeline produced scientifically correct results.**

### Figures (saved, verified visually)
- `figures/fig1_qc_violin.png` — genes/UMIs/%MT distributions
- `figures/fig2_qc_scatter.png` — counts vs genes scatter
- `figures/fig3_umap_clusters.png` — UMAP with 7 Leiden clusters labeled on-data
- `figures/highly_variable_genes_hvg.png` — HVG dispersion plot
- `figures/rank_genes_groups_leiden_marker_genes.png` — top-10 marker scores per cluster

### Results files
- `results/qc_stats.json`, `results/clustering.json`, `results/pipeline_log.json`
- `results/pbmc3k_processed.h5ad` (full annotated matrix, 40 MB)
- Runner: `scripts/run_scrna_experiment.py`

---

## Step-by-step findings

### 1. What skills exist in `src/openscience/skills/bioinformatics/`?
**None.** `src/openscience/skills/` **did not exist at all.** All 111 agents call
`self.run_skill(<name>, ...)`, but `AgentOrchestrator.execute_skill`
(src/openscience/core/orchestrator.py:164-185) is a **hard-coded stub** that returns
`{"skill": ..., "operation": ..., "status": "ok", "data": kwargs}` — no tool ever runs.
The `data_ingestor`, `qc_analyzer`, `scanpy_specialist`, `matplotlib_stylist`,
and `publication_formatter` agents all existed as thin shells over the stub. The
`docs/agents.md` catalog advertises "100 agents", but none of them could do anything.

### 2. What I implemented
- **`src/openscience/skills/__init__.py` + `skills/bioinformatics/{__init__,skill}.py`** —
  the first real skill backend: `BioinformaticsSkill` dispatching `bioio` (10x mtx / h5ad /
  csv loading), `scanpy` (`qc_analysis`, `run` = normalize→HVG→PCA→neighbors→UMAP→Leiden→
  markers), `anndata` introspection, and `matplotlib` style application. AnnData is shared
  between agents via the orchestrator context dict.
- **`scripts/run_scrna_experiment.py`** — `RealBioOrchestrator(AgentOrchestrator)` that
  routes `execute_skill` to `BioinformaticsSkill`, then drives the real agents:
  data_ingestor → qc_analyzer → scanpy_specialist → matplotlib_stylist / publication_formatter.
- Installed `scanpy`, `anndata`, `leidenalg`, `python-igraph` into the project `.venv`
  (pandas/numpy/matplotlib/scipy/sklearn/seaborn were already there).

### 3. Errors hit & fixes (all real)

| # | Error | Root cause | Fix |
|---|---|---|---|
| 1 | `ValueError: Length of passed value for var_names is 32738, but this AnnData has shape: (32738, 2700)` | `sc.read_mtx` loads 10x matrices genes×cells literally; they must be transposed to cells×genes. | `.T` after `read_mtx`. |
| 2 | Silent/truncated crash on run (traceback cut mid-frame, empty error file) | Script bug: `ROOT = Path(__file__).parent` pointed at `scripts/`, so the input path didn't exist and the FileNotFoundError surfaced inside async unwinding confusingly. | `ROOT = ... .parent.parent`. |
| 3 | QC reported `median_pct_mito: 0.0`, `cells_with_mt_detected: 0` — scientifically wrong | 10x hg19 `genes.tsv` col 0 = Ensembl IDs (used as var_names); `MT-` prefix exists only on gene **symbols**. | Promote symbols to `var_names`, keep Ensembl in `var['ensembl_ids']`; detect MT on symbols. |
| 4 | `AttributeError: 'numpy.ndarray' object has no attribute 'values'` | `pd.Index.str.startswith()` already returns ndarray; chained `.values`. | `.to_numpy()` via `pd.Series`. |
| 5 | Marker-gene plot showed Ensembl IDs, not symbols | `rank_genes_groups` ran on `adata.raw` whose var_names were Ensembl. | Same fix as #3 — symbols as var_names everywhere. |

After fixes 1–5 the pipeline ran clean, exits 0, and markers map 1:1 to canonical PBMC cell types.

---

## Can the tool analyze real single-cell data?

**Yes after implementing the skills — out of the box, no.**

**What works well:**
- The agent contract (`BaseAgent.run_skill` → `orchestrator.execute_skill`) is a clean
  seam; dropping in a real backend required **zero changes to any agent code**.
- Agent auto-selection (`_select_agent` keyword routing), agent registry (111 classes
  load), `Result.coerce`, and async `_run_awaitable` all functioned.
- Passing one AnnData object through the shared context made the four-agent pipeline
  (load → QC → cluster → plot) genuinely compose.

**What's missing / needs to be built:**
1. **All skill implementations.** `src/openscience/skills/` didn't exist. Only
   bioinformatics basics now exist; the other ~15 advertised skill providers
   (pubmed_api, bioio full formats, multiqc, deseq2, style_sheets, citation_graph, …)
   are all stubs returning `{"status": "ok"}`.
2. **A production `execute_skill` dispatcher.** Skills must be registered/bound to the
   orchestrator (registry dict), not monkey-patched per experiment. The base
   orchestrator should raise `NotImplementedError` instead of returning fake success —
   the stub silently "succeeds", which would corrupt science if unnoticed.
3. **Shared-state contract.** Context keys (`adata`, `qc_stats`, ...) are informal;
   typing/validation (e.g., pydantic models or a DataExchange protocol) would prevent
   silent `None` data bugs (the `qc_analyzer` silently accepts `data=None`).
4. **Error surfacing.** Async exceptions inside `execute_skill` produced confusingly
   truncated tracebacks; the sandbox runner should capture and re-raise with context.
5. **Visualization agents** currently only apply rcParams; real figure rendering runs
   through scanpy's `save=` API. A `matplotlib.render(figure_data, viz_type)` backend
   (decoupled from scanpy) would make the viz agents honest.
6. **Data ingester** needs a 10x *directory* mode (`sc.read_10x_mtx`), h5ad round-trip
   validation, and `loom`/`zarr` readers (currently only mtx/h5ad/csv).
7. **Tests for the skill layer** — the repo's 100+ tests never touch a skill's output,
   which is why the all-stub state shipped unnoticed.

## Commands to reproduce
```bash
cd /Users/srubaiat/openScience
.venv/bin/pip install scanpy python-igraph leidenalg
curl -sL -o experiments/data_analysis_report/data/pbmc3k.tar.gz \
  https://cf.10xgenomics.com/samples/cell/pbmc3k/pbmc3k_filtered_gene_bc_matrices.tar.gz
tar xzf experiments/data_analysis_report/data/pbmc3k.tar.gz -C experiments/data_analysis_report/data
.venv/bin/python scripts/run_scrna_experiment.py
```
