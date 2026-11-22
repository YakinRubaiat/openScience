#!/usr/bin/env python
"""Real literature review experiment: CRISPR in cancer therapy.

Drives the openScience agents (pubmed_search, lit_summarizer, trend_tracker)
through the RealSkillOrchestrator and writes all artifacts to experiments/.
"""

import json
import sys
from pathlib import Path

# Use src/ directly so edits take effect without reinstalling
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from openscience.core.real_orchestrator import RealSkillOrchestrator

OUT = Path(__file__).resolve().parent
OUT.mkdir(exist_ok=True)


def main():
    orch = RealSkillOrchestrator()
    print(f"Loaded {len(orch.agents)} agents")
    print(f"Loaded {len(orch.skill_registry)} skills: {sorted(orch.skill_registry)}")

    # --- Step A: PubMed search ---
    print("\n[A] Running pubmed_search agent...")
    search_result = orch.execute_agent(
        "pubmed_search",
        parameters={
            "query": "CRISPR cancer therapy",
            "max_results": 60,
            "date_from": "2020",
            "date_to": "2026",
        },
        context={},
    )
    # Result.coerce has already unwrapped the agent's format_result(),
    # so search_result.data is the inner dict {papers, count, query, ...}
    papers = search_result.data.get("papers", [])
    print(f"   Retrieved {len(papers)} papers")
    (OUT / "papers_raw.json").write_text(json.dumps(papers, indent=2))
    print(f"   Wrote {OUT/'papers_raw.json'}")

    # --- Step B: Literature summarization ---
    print("\n[B] Running lit_summarizer agent...")
    summary_result = orch.execute_agent(
        "lit_summarizer",
        parameters={
            "topic": "CRISPR gene editing in cancer therapy",
            "papers": papers,
            "max_papers": 30,
        },
        context={"papers": papers},
    )
    (OUT / "synthesis.json").write_text(json.dumps(summary_result.data, indent=2, default=str))
    print(f"   Wrote {OUT/'synthesis.json'}")

    # --- Step C: Trend tracking ---
    print("\n[C] Running trend_tracker agent...")
    trend_result = orch.execute_agent(
        "trend_tracker",
        parameters={"papers": papers, "n_topics": 6, "n_top_words": 10},
        context={"papers": papers},
    )
    (OUT / "trends.json").write_text(json.dumps(trend_result.data, indent=2, default=str))
    print(f"   Wrote {OUT/'trends.json'}")

    # --- Console summary ---
    print("\n=== Quick summary ===")
    sd = summary_result.data
    print(f"Topic: {sd.get('topic')}")
    print(f"Papers: {sd.get('n_papers')}, summarized: {sd.get('n_summarized')}")
    synthesis = sd.get("synthesis", {})
    print(f"Yearly distribution: {synthesis.get('years')}")
    print(f"Top journals: {[j for j,_ in synthesis.get('top_journals', [])[:5]]}")
    print(f"Top MeSH: {[m for m,_ in synthesis.get('top_mesh_terms', [])[:10]]}")

    td = trend_result.data
    print(f"\nTopics discovered:")
    for t in td.get("topics", [])[:6]:
        print(f"  - {t.get('topic_id')}: {', '.join(t.get('top_words', [])[:6])}")
    print(f"\nEmerging MeSH terms:")
    for e in td.get("emerging_mesh", [])[:8]:
        print(f"  - {e['term']}: +{e['delta']} (n={e['new_count']})")


if __name__ == "__main__":
    main()
