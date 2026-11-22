# Experiment: Can openScience actually help write a scientific manuscript?

**Date:** 2026-11-22
**Goal:** Use openScience writing agents (`abstract_writer`, `introduction_writer`,
`methods_writer`, `results_writer`, `discussion_writer`, `citation_manager`) to
draft a mini-manuscript around a simulated finding — "Novel compound AZ-47
inhibits KRASG12C-mutant tumor growth in vitro" — and record what works, what
is missing, and what had to be implemented.

---

## Step 1 — Do writing skills exist in `src/openscience/skills/writing/`?

**Tried:** `ls src/openscience/skills/writing/`

**Finding:** The directory existed but contained only `__init__.py` (all other
skills directories were likewise empty or near-empty). The agents in
`src/openscience/agents/writing/` are thin shells that call
`self.run_skill("scientific_writing", ...)` etc. — but the default
`AgentOrchestrator.execute_skill()` was a stub that simply echoed its arguments
back (`{"status": "ok", "data": kwargs}`). **No real writing skill
implementations were wired in.**

## Step 2 — Implement the missing writing skills

**What had to be implemented/fixed:**

1. **A skill registry** — added `register_skill` / `get_skill` /
   `load_default_skills` to `src/openscience/skills/__init__.py`, and modified
   `AgentOrchestrator.__init__` to load the built-in skills and
   `execute_skill()` to dispatch to a registered skill when one exists
   (falling back to the old echo-stub otherwise).
2. **`scientific_writing` / `results_writing` / `discussion_writing` skills**
   (`skills/writing/scientific_writing.py`). Since **no LLM API key is
   available in this environment** (only `ANTHROPIC_BASE_URL` is set, no
   `ANTHROPIC_API_KEY`), these were implemented as a deterministic
   *template engine*: structured research content in → IMRaD-style prose out,
   with sentence-boundary-aware word-limit trimming for the abstract.
3. **`pubmed_api` skill** (`skills/writing/pubmed.py`) — a **real** HTTP client
   against NCBI E-utilities (`esearch` + `efetch`), no API key required.
4. **`bibtex` skill** (`skills/writing/citation.py`) — formats references as
   numbered Vancouver or APA citations and generates BibTeX entries.

**Errors encountered during the experiment:**

| Error | Cause | Fix |
|---|---|---|
| `ImportError: cannot import name 'skills'` | The venv had a stale *non-editable* install of `openscience` shadowing `src/` | `pip install -e . --no-deps` |
| Skill registry empty after install | stale `__pycache__` | cleared `__pycache__` |
| `AttributeError: 'NoneType'` in experiment script | `Result.coerce` already unwraps the agent's `format_result`; script double-unwrapped `.data.data` | use `res.data` directly |
| sed mangled the script | overlapping replacement | rewrote the two lines manually |
| Discussion printed "Our study has limitations:" 3× | per-item prefixing bug in my template | emit one lead-in sentence |
| Missing periods between generated sentences | templates concatenated raw fields | added `_end_period()` helper |
| "et al.." double period in Vancouver style | trailing period in `et al.` then `.` from template | drop the embedded period |

Pre-existing failure note: `tests/api/test_auth.py::test_register_and_login`
fails even on a clean checkout (confirmed via `git stash`), i.e. **unrelated to
this experiment**. The full test suite (`pytest tests --ignore=tests/integration`)
passes: **196 passed**.

## Steps 3–10 — Running the pipeline

The full pipeline ran end-to-end via
`experiments/manuscript_draft/run_experiment.py`. Per-step (tried / errors /
fixes / content) is logged in `experiment_log.json`; the actual text is in
`manuscript.md`. Highlights of the produced content:

- **Abstract (149/200 words):** coherent background → gap → aim → methods →
  results → conclusion arc, correctly hedged.
- **Introduction:** classic three-paragraph structure (field → gap+significance
  → aim/approach/principal finding).
- **Methods:** subheaded paragraphs (Study design / Model system / Compounds /
  Assays / Statistical analysis) in past tense with ATCC authentication,
  mycoplasma testing, DMSO limits, ANOVA details — reads like a real methods
  section because the structured input was detailed.
- **Results:** three numbered findings with IC50 values, figure callouts
  (Fig. 1A–C), and inline statistics.
- **Discussion:** principal finding → interpretation → comparison with
  literature → mechanism → limitations → future directions → conclusion.
- **References (real):** 7 unique papers fetched live from PubMed (NCBI
  E-utilities), including the seminal Ostrem 2013 *Nature* switch-II pocket
  paper (PMID 23784726), Awad 2021 *NEJM* acquired-resistance paper
  (PMID 34161704), formatted in Vancouver style + a `references.bib`.

## Deliverables

- `experiments/manuscript_draft/manuscript.md` — complete mini-manuscript
- `experiments/manuscript_draft/references.bib` — BibTeX from real PubMed data
- `experiments/manuscript_draft/experiment_log.json` — per-step log
- `experiments/manuscript_draft/run_experiment.py` — reproducible driver
- `experiments/manuscript_draft/simulated_finding.json` — the simulated finding
- New/improved: `src/openscience/skills/__init__.py` (registry),
  `src/openscience/skills/writing/{scientific_writing,pubmed,citation}.py`,
  orchestrator skill dispatch.

## Verdict: Can this tool actually help write a scientific paper?

**Yes — but the help is structural, not generative, until an LLM is wired in.**

What works today:
- The agent→skill→orchestrator architecture is real and extensible; once the
  registry was added, all six writing agents worked with no agent-code changes.
- The PubMed skill is genuinely useful: real literature retrieval + formatted
  citations + BibTeX, end-to-end, no hallucinated references.
- The template engine produces well-structured, correctly hedged IMRaD prose —
  *provided the human supplies the scientific content* (claims, numbers,
  interpretations) in structured form.

What's missing / would make it substantially better:
1. **An LLM backend for the writing skills.** The `general/llm_summarization`
   skill name suggests this was planned. With an API key, the skills could
   draft prose from bullet points instead of requiring fully-written inputs.
2. **A figure pipeline feeding Results.** Results text references "Fig. 1A–C"
   but nothing generates the figures; `figure_generation` experiments exist
   separately but are not connected to `results_writer`.
3. **In-text citation markers.** References are listed but not cited as `[1]`
   in the body text; citation placement is manual.
4. **Journal-format export** (journal_formatter agent exists but its skill is
   also unimplemented) — no DOCX/PDF/LaTeX output path.
5. **Section cross-consistency checks** (e.g. verifying every number in Results
   appears in Methods) are absent.
6. The default `execute_skill` stub silently echoes kwargs for unimplemented
   skills — failure is *silent*, which made the missing-skill problem non-obvious
   at first. The registry now fixes this for registered skills, but unknown
   skill names still fall back to the stub rather than raising.
