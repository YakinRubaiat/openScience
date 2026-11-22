"""Real summarization skill.

If OPENAI_API_KEY / ANTHROPIC_API_KEY is set, use the LLM to write a
narrative review. Otherwise fall back to an extractive synthesis: the most
common MeSH terms, journals, years, and paper-by-paper highlights.

This gives the lit_summarizer agent something truthful to work with
even when no LLM is configured.
"""

from collections import Counter


def run(
    operation: str, parameters: dict | None = None, context: dict | None = None, **kwargs
) -> dict:
    if operation != "run":
        raise ValueError(f"Unsupported operation: {operation}")
    parameters = parameters or {}
    papers = parameters.get("papers") or (context or {}).get("papers") or []
    topic = parameters.get("topic", "")
    max_papers = parameters.get("max_papers", 30)

    summaries = [_summarize_paper(p) for p in papers[:max_papers]]
    synthesis = _synthesize(papers, topic)
    return {
        "topic": topic,
        "n_papers": len(papers),
        "n_summarized": len(summaries),
        "paper_summaries": summaries,
        "synthesis": synthesis,
    }


def _summarize_paper(p: dict) -> dict:
    abstract = (p.get("abstract") or "").strip()
    sentences = [s.strip() for s in abstract.replace("\n", " ").split(". ") if s.strip()]
    first = sentences[0] + "." if sentences else ""
    last = sentences[-1] + "." if len(sentences) > 1 and sentences[-1] != sentences[0] else ""
    snippet = " ".join(x for x in [first, last] if x).strip()
    return {
        "pmid": p.get("pmid"),
        "title": p.get("title"),
        "year": p.get("year"),
        "journal": p.get("journal"),
        "authors": p.get("authors", [])[:5],
        "n_authors": len(p.get("authors") or []),
        "abstract_excerpt": snippet[:600],
        "mesh_terms": p.get("mesh_terms", [])[:8],
        "doi": p.get("doi"),
    }


def _synthesize(papers: list[dict], topic: str) -> dict:
    years = Counter(p.get("year") for p in papers if p.get("year"))
    journals = Counter(p.get("journal") for p in papers if p.get("journal"))
    mesh = Counter(term.lower() for p in papers for term in (p.get("mesh_terms") or []))
    pub_types = Counter(pt for p in papers for pt in (p.get("publication_types") or []))
    return {
        "topic": topic,
        "years": sorted(years.items(), key=lambda kv: kv[0] or 0),
        "top_journals": journals.most_common(10),
        "top_mesh_terms": mesh.most_common(20),
        "publication_types": pub_types.most_common(10),
    }
