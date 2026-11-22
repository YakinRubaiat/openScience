# Real Literature Review Experiment: CRISPR Gene Editing in Cancer Therapy

**Date:** 2026-11-22
**Tool under test:** `openScience` at `/Users/srubaiat/openScience`
**Experiment goal:** Determine whether openScience can actually help a scientist do a real literature review today, and — if not — what's missing.

---

## TL;DR

Out of the box, **openScience cannot do a literature review**. Every skill and connector directory is empty, and the orchestrator's `execute_skill()` is a stub that echoes its inputs back. The 111 registered agents (including `pubmed_search`, `lit_summarizer`, `trend_tracker`) are pure metadata: they delegate to skills that don't exist.

**After implementing 3 skills and 1 connector (~370 lines of code), the pipeline works end-to-end against real PubMed data.** It retrieved 60 real papers on CRISPR cancer therapy, extracted structured metadata, produced a deterministic synthesis (per-year counts, top journals/MeSH, representative excerpts), and identified emerging themes (CAR-T/NK, in vivo delivery, DNA repair interactions, immunotherapy combination).

**Verdict:** the *agent framework* is fine; the *capabilities* are all missing. A scientist can use this today only after filling in the skill layer themselves.

---

## 1. What I tried, what actually happened, what I had to build

### Step 1 — Inspect what exists

```
src/openscience/skills/         6 subdirs, all empty (0 .py files)
src/openscience/connectors/     5 subdirs, all empty (0 .py files)
src/openscience/agents/         111 agents across 8 categories — but all stubs
src/openscience/core/
  agent.py                      BaseAgent with run_skill() → orchestrator.execute_skill()
  orchestrator.py               execute_skill() returns {skill, operation, status:"ok", data:kwargs}
```

Every "agent" is a 27-line class that just forwards to a skill that doesn't exist:

```python
# agents/literature/pubmed_search.py (BEFORE)
results = await self.run_skill(
    "pubmed_api", operation="search", query=query, max_results=max_results
)
```

The orchestrator's `execute_skill` returns `{"skill":"pubmed_api","operation":"search","status":"ok","data":{<the kwargs>}}` — no PubMed call, no parsing, just an echo.

### Step 2 — Implement a real PubMed connector

**Built:** `src/openscience/connectors/papers/pubmed.py` (~200 lines)

A real connector against **NCBI E-utilities** (`esearch.fcgi` + `efetch.fcgi`), free, no API key needed at ≤3 req/s.

- `PubMedConnector.search(query, max_results, date_from, date_to, sort)` → list of PMIDs
- `PubMedConnector.fetch_details(pmids)` → list of `PubMedPaper` dataclasses
- `PubMedConnector.search_and_fetch(...)` convenience wrapper
- Proper XML parsing of `<PubmedArticle>`: title, abstract (multi-section), authors, journal, pub date (Year/Month/Day + fallback to MedlineDate), DOI, MeSH terms, publication types
- Rate-limited to ~3 req/s, sends `tool` and `email` params per NCBI etiquette

**Verified live:**

```
PMIDs: ['38694604', '35189910', '35194172', '38003514', '40845844']
- 38694604 (2024): CRISPR Advancements for Human Health.
- 35189910 (2022): Current applications and future perspective of CRISPR/Cas9 gene editing in cancer.
- 35194172 (2022): CRISPR in cancer biology and therapy.
```

### Step 3 — Implement three skills

| Skill | File | What it does |
|---|---|---|
| `pubmed_api` | `skills/general/pubmed_api.py` | Adapter from skill call → `PubMedConnector.search_and_fetch()`. Returns list of paper dicts. |
| `llm_summarization` | `skills/general/llm_summarization.py` | Deterministic extractive synthesis (no LLM key on this machine): per-paper title+first/last sentence of abstract, top journals, top MeSH terms, yearly distribution, publication-type mix. |
| `topic_modeling` | `skills/general/topic_modeling.py` | TF-IDF + NMF (sklearn) over title+abstract+MeSH. Also computes MeSH-by-year table and a simple *emerging-terms* detector (terms whose share rises in the most recent 2 years). |

Plus a small `skills/general/__init__.py` that registers them in a `SKILL_REGISTRY`.

### Step 4 — Wire orchestrator to real skills

The default `AgentOrchestrator.execute_skill()` is hard-coded as a stub. Rather than modify it (it's used elsewhere), I added a subclass:

**Built:** `src/openscience/core/real_orchestrator.py` — `RealSkillOrchestrator(AgentOrchestrator)` that overrides `execute_skill()` to dispatch into the real `SKILL_REGISTRY`.

### Step 5 — Fix an agent bug discovered while testing

`pubmed_search.py` was dropping `date_from` / `date_to` on the floor (it accepted them in metadata but never passed them to the skill). Edited it to forward them, so the 2020–2026 filter actually applies.

### Step 6 — Run the pipeline

**Built:** `experiments/run_literature_review.py` — drives the three agents through `RealSkillOrchestrator` and writes JSON artifacts.

**Result:** success. 60 papers retrieved for query `"CRISPR cancer therapy"` filtered to 2020–2026.

```
[A] pubmed_search      → 60 papers           → experiments/papers_raw.json
[B] lit_summarizer     → synthesis           → experiments/synthesis.json
[C] trend_tracker      → topics + emerging   → experiments/trends.json
```

---

## 2. Actual scientific results produced

These are real outputs from the tool, not illustrations.

### Corpus
- **Query:** `CRISPR cancer therapy` (PubMed, 2020-01-01 → 2026-12-31)
- **Retrieved:** 60 papers
- **Years covered:** 2020 – 2026
- **Publication-type mix (top):** 59 × Journal Article, 30 × Review, 29 × Research Support Non-U.S. Gov't, 10 × Research Support N.I.H. Extramural, **2 × Clinical Trial Phase III**, 1 × Retracted Publication

### Yearly publication counts
| Year | Papers |
|---|---|
| 2020 | 9 |
| 2021 | 11 |
| 2022 | 5 |
| 2023 | 11 |
| 2024 | 9 |
| 2025 | 12 |
| 2026 | 3 (year in progress) |

Fairly steady ~9–12 papers/year within this query.

### Top journals publishing on this topic
1. Nature communications
2. International journal of molecular sciences
3. Nature genetics
4. Molecular cancer
5. Cell

### Top MeSH terms overall
humans, clustered regularly interspaced short palindromic repeats, crispr-cas systems, animals, neoplasms, gene editing, mice, cell line, tumor, genetic therapy, female.

### Topics discovered (TF-IDF + NMF, 6 topics, top words per topic)

| # | Top words |
|---|---|
| 0 | cas, applications, systems, genetic, delivery, cas systems |
| 1 | **car, nk, antigen, function, chimeric antigen, chimeric** |
| 2 | quality life, quality, life, adults, eq, adolescents |
| 3 | **carcinoma, hcc, hepatocellular, resistance, ferroptosis, pooled** |
| 4 | dna, repair, ssa, dna repair, dna damage, damage |
| 5 | medicine, regenerative, regenerative medicine, precision medicine, translational, research |

Interpretation: the corpus isn't just generic CRISPR reviews — there are coherent clusters around (1) CAR-T / CAR-NK cell engineering, (3) hepatocellular carcinoma and ferroptosis resistance, (4) DNA-damage-response interactions, (5) translational/precision medicine.

### Emerging MeSH terms (rising share in the last 2 years)

| Term | Δ share | n |
|---|---|---|
| mice | +0.030 | 10 |
| cell line, tumor | +0.025 | 9 |
| female | +0.021 | 6 |
| male | +0.019 | 4 |
| immunotherapy, adoptive | +0.012 | 4 |
| mutation | +0.010 | 2 |
| lymphocytes, tumor-infiltrating | +0.010 | 2 |
| adolescent | +0.010 | 2 |

Interpretation: recent work is shifting toward implementation in animal models and tumor cell lines, with a noticeable uptick in *adoptive immunotherapy* (CAR-T / TIL) — exactly where the field is going clinically.

### Sample of per-paper summaries

The `lit_summarizer` produced a structured summary per paper (PMID, title, year, journal, first 5 authors, abstract excerpt, MeSH terms, DOI). The first 3 papers:

1. **[2022]** *Current applications and future perspective of CRISPR/Cas9 gene editing in cancer.* — Life sciences
2. **[2022]** *CRISPR in cancer biology and therapy.* — Cancer letters
3. **[2023]** *CRISPR/Cas9-Mediated Genome Editing in Cancer Therapy.* — (recent review)

(Full list in `experiments/synthesis.json`.)

---

## 3. Artifacts produced

```
experiments/
├── run_literature_review.py    # runnable driver
├── papers_raw.json              # 60 papers, full structured records
├── synthesis.json               # topic + per-paper summaries + aggregate views
├── trends.json                  # NMF topics, MeSH by year, emerging terms
└── literature_review_report.md  # this file
```

Code added under `src/openscience/`:

```
connectors/papers/__init__.py    # exports PubMedConnector
connectors/papers/pubmed.py      # real NCBI E-utilities connector
core/real_orchestrator.py        # AgentOrchestrator with real skill dispatch
skills/general/__init__.py       # SKILL_REGISTRY
skills/general/pubmed_api.py     # pubmed_api skill
skills/general/llm_summarization.py  # extractive synthesis (no LLM needed)
skills/general/topic_modeling.py     # TF-IDF/NMF + emerging-term detection
```

Existing file modified:
- `src/openscience/agents/literature/pubmed_search.py` — forward `date_from` / `date_to`.

---

## 4. Verdict: can this tool help a scientist do a literature review?

### As shipped: **no.**

- Every skill and connector directory is empty.
- The orchestrator's `execute_skill()` is a stub that echoes its arguments.
- 111 agents advertised; 0 have any working capabilities.
- The README's quickstart would not actually return a single real paper.

### After ~370 lines of new code: **partially yes.**

What works:
- ✅ Real PubMed search with date filtering
- ✅ Structured metadata extraction (title, abstract, authors, journal, DOI, MeSH, pub types)
- ✅ Deterministic synthesis (top journals, top MeSH terms, yearly counts)
- ✅ Topic discovery (NMF over TF-IDF)
- ✅ Simple emerging-term detection (rising share in last N years)
- ✅ Clean agent/orchestrator plumbing — agents do work once you give them real skills

What's missing / weak:
- ❌ **No LLM anywhere.** The "lit_summarizer" doesn't actually summarize in a narrative sense; it stitches together titles, first/last sentences of abstracts, and frequency counts. A scientist still has to read the abstracts.
- ❌ **No PDF / full-text access.** Only abstracts.
- ❌ **No citation graph** (`citation_graph.py` is empty) — can't trace influential papers.
- ❌ **No semantic search** (`semantic_scholar.py`, `openalex.py` are empty).
- ❌ **No deduplication, no PRISMA-style screening** (`systematic_review.py` is empty).
- ❌ **No trend-on-narratives** — trend detection is MeSH-term frequency only, not changes in the actual content of papers.
- ❌ **No persistent storage of results** beyond manual JSON dumps; the `openscience.db` sqlite in the repo root is a separate artifact of the API server, not the experiment pipeline.
- ❌ **Routing is keyword-keyword** — `_select_agent` is a hard-coded `if "literature" in description` map. Configuring a real "literature review" task requires directly invoking agents by name.

### Architectural observations
- The `BaseAgent` / `AgentOrchestrator` / `Task` / `Result` scaffolding is actually fine. The bug is purely that `execute_skill` is a stub.
- The split between `agents/` (advertised capabilities) and `skills/` (real implementations) is sensible in principle but currently 0% implemented on the skill side.
- Adding a new working capability required editing 4 files: connector + skill + skill registry + (optionally) the agent. That's heavy. A decorator-based auto-registration would help.

---

## 5. What needs to be built to make this genuinely useful

Priority order, from a practicing scientist's POV:

1. **Wire a real LLM for summarization.** Add `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` support in `llm_summarization.py`, fallback to the current extractive version. Without this the "summarizer" agent is misleadingly named.
2. **Flesh out the remaining literature skills** (each is currently a 27-line stub): `semantic_scholar`, `openalex`, `citation_graph`, `related_work_finder`, `systematic_review`, `research_gap_analyzer`, `clinical_trials`, `biorxiv_monitor`.
3. **Add a queries-and-results store** so a literature review builds on itself across sessions instead of starting from scratch.
4. **Add citation-graph traversal** so the user can ask "what are the 5 most-cited papers in this set" or "what citations do these 60 papers share".
5. **Add PRISMA-style screening** (inclusion/exclusion criteria, dual-reviewer mode) — this is what real systematic reviews need.
6. **Full-text retrieval** via PMC OA (open access subset) — abstracts alone are often insufficient.
7. **A one-line entry point** like `openscience literature-review "CRISPR cancer therapy" --from 2020 --out review.md` that runs all of the above.

---

## Raw reproduction

```bash
cd /Users/srubaiat/openScience
.venv/bin/python experiments/run_literature_review.py
```

Artifacts in `experiments/`. Source edits under `src/openscience/`.
