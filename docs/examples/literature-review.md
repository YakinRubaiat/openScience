# Example: Literature Review Automation

From a research question to a PRISMA-compliant systematic review with a
formatted bibliography.

**Agents used:** `pubmed_search` → `systematic_review` → `lit_summarizer` →
`citation_manager`

## Workflow

```python
from openscience import ScienceSession

session = ScienceSession()

# 1. Search PubMed/PMC for the question
search = session.analyze(
    task="Search for CRISPR screens in glioblastoma, 2020-2026",
    specialist="pubmed_search",
    date_range=("2020-01-01", "2026-12-31"),
)

# 2. PRISMA screening: deduplicate, title/abstract screen, full-text screen
review = session.analyze(
    task="Screen these results following PRISMA guidelines",
    specialist="systematic_review",
    input_results=search.paper_list,
)

# 3. Summarize each included paper
summaries = session.analyze(
    task="Summarize key findings and methods of included papers",
    specialist="lit_summarizer",
    input_papers=review.included,
)

# 4. Synthesize and format references
synthesis = session.write_section(
    summaries,
    section="literature_review",
)

bibliography = session.analyze(
    task="Format all citations in Vancouver style",
    specialist="citation_manager",
    input_references=review.included,
)

print(synthesis)
```

## Expected Artifacts

| Artifact | Description |
|----------|-------------|
| `review/prisma_flow.svg` | PRISMA flow diagram |
| `review/included.csv` | Included papers with screening decisions |
| `review/summaries.md` | Per-paper structured summaries |
| `review/synthesis.md` | Narrative synthesis |
| `review/references.bib` | Formatted bibliography |

## Notes

- Engineering-network destinations used here (NCBI E-utilities) require no
  key by default, but registration speeds things up:
  `openscience credentials set ncbi` (see [Configuration](../configuration.md)).
- Swap `pubmed_search` for `openalex` or `semantic_scholar` to broaden
  coverage beyond biomedical literature.
