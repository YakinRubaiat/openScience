"""Real scientific writing experiment using openScience agents.

Runs each writing agent against the skill implementations and assembles a
mini-manuscript. Every step logs what was tried, errors, fixes, and output.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from openscience.core.orchestrator import AgentOrchestrator

OUT = Path(__file__).parent
LOG: list[dict] = []


def log(step: str, tried: str=None, error: str=None, fix: str=None, content: str=None):
    entry = {"step": step, "tried": tried, "error": error, "fix": fix}
    if content is not None:
        entry["content"] = content
    LOG.append(entry)
    print(f"\n=== {step} ===")
    if tried:
        print(f"TRIED: {tried}")
    if error:
        print(f"ERROR: {error}")
    if fix:
        print(f"FIX: {fix}")
    if content is not None:
        print("CONTENT:\n" + (content if isinstance(content, str) else json.dumps(content, indent=2)))


def step(name, fn):
    try:
        return fn()
    except Exception:
        err = traceback.format_exc()
        log(name, error=err)
        raise


orch = AgentOrchestrator()

finding = json.loads((OUT / "simulated_finding.json").read_text())

# ---------------------------------------------------------------------------
# Step 4: abstract_writer
# ---------------------------------------------------------------------------
def do_abstract():
    params = {
        "paper_content": {
            "background": f"KRAS is the most frequently mutated oncogene in human cancer, and the {finding['target']} allele occurs in ~13% of lung adenocarcinomas.",
            "gap": "Although covalent G12C inhibitors such as sotorasib and adagrasib have reached the clinic, acquired resistance and incomplete pathway suppression limit durable responses, and additional chemical matter with differentiated profiles remains valuable.",
            "aim": f"We characterized {finding['compound']}, a novel covalent {finding['target']} inhibitor, in preclinical models of {finding['disease']}.",
            "methods": f"We measured viability across a panel of KRASG12C-mutant ({', '.join(finding['cell_lines'])}) and KRAS wild-type (A549) NSCLC cell lines, profiled signaling by immunoblot, and quantified apoptosis by caspase-3/7 activation and PARP cleavage.",
            "results": f"{finding['key_finding']}",
            "conclusion": f"These data nominate {finding['compound']} as a potent and selective preclinical {finding['target']} inhibitor and provide a framework for evaluating next-generation KRAS-targeted agents.",
        },
        "target_journal": "Cancer Research",
        "word_limit": 200,
    }
    res = orch.execute_agent("abstract_writer", params, {})
    data = res.data
    abstract = data.get("abstract", "") if isinstance(data, dict) else str(data)
    log("Step 4: abstract_writer", tried="execute_agent('abstract_writer', paper_content=<structured finding>)", content=f"[{data.get('word_count')} words / limit {data.get('word_limit')}]\n\n{abstract}")
    return abstract

abstract = step("Step 4: abstract_writer", do_abstract)

# ---------------------------------------------------------------------------
# Step 5: introduction_writer
# ---------------------------------------------------------------------------
def do_introduction():
    params = {
        "field": "oncogenic KRAS signaling and its pharmacological targeting",
        "established_knowledge": (
            "KRAS is the most frequently mutated oncogene in human cancer, with activating mutations detected in "
            "approximately 25% of all tumors. For more than three decades KRAS was considered undruggable because its "
            "smooth protein surface lacks tractable binding pockets. The discovery of a cryptic switch-II pocket in the "
            "GDP-bound state of the KRASG12C mutant enabled the first covalent inhibitors, culminating in the approval "
            "of sotorasib and adagrasib for KRASG12C-mutant non-small cell lung cancer (NSCLC)."
        ),
        "knowledge_gap": (
            "clinical responses to first-generation G12C inhibitors are often modest and transient: median progression-free "
            "survival is roughly 6-7 months, and resistance emerges through RTK reactivation, secondary KRAS mutations, and "
            "MAPK pathway bypass. Moreover, many covalent scaffolds show incomplete target engagement in vivo."
        ),
        "significance": (
            "identifying chemically distinct inhibitors with deeper pathway suppression could improve response durability "
            "and provide back-up compounds for combination strategies"
        ),
        "aim": f"characterize the cellular pharmacology of {finding['compound']}, a novel covalent {finding['target']} inhibitor, across a panel of NSCLC models",
        "approach": (
            f"we profiled antiproliferative activity in three KRASG12C-mutant cell lines "
            f"({', '.join(finding['cell_lines'])}) and the KRAS wild-type A549 line, and we examined downstream "
            "signaling and apoptosis using immunoblotting and caspase assays"
        ),
        "principal_finding": finding["key_finding"],
    }
    res = orch.execute_agent("introduction_writer", params, {})
    intro = res.data
    log("Step 5: introduction_writer", tried="execute_agent('introduction_writer', field/established_knowledge/knowledge_gap/aim/...)", content=intro)
    return intro

introduction = step("Step 5: introduction_writer", do_introduction)

# ---------------------------------------------------------------------------
# Step 6: methods_writer
# ---------------------------------------------------------------------------
def do_methods():
    methods_result = {
        "study_design": (
            "All experiments were performed as three independent biological replicates. Dose-response studies used "
            "10-point, 3-fold serial dilutions of AZ-47 (0.1 nM to 10 uM)."
        ),
        "model_system": (
            "Human NSCLC cell lines NCI-H358, NCI-H1373, and NCI-H2122 (KRASG12C-mutant) and A549 (KRAS wild-type) "
            "were obtained from ATCC, authenticated by short tandem repeat profiling, and cultured in RPMI-1640 "
            "supplemented with 10% fetal bovine serum at 37 C in 5% CO2. Lines were routinely tested and found "
            "negative for mycoplasma."
        ),
        "compounds": (
            "AZ-47 (purity >98% by LC-MS) was synthesized in-house and dissolved in DMSO; final DMSO concentration "
            "did not exceed 0.1% (v/v). Sotorasib (AMG 510) was used as a reference inhibitor."
        ),
        "assays": (
            "Cell viability was measured 72 h after compound addition using CellTiter-Glo (Promega); IC50 values were "
            "derived from four-parameter logistic fits. Signaling was assessed by immunoblotting of whole-cell lysates "
            "with antibodies against phospho-ERK1/2 (Thr202/Tyr204), total ERK1/2, cleaved PARP, and GAPDH. Apoptosis "
            "was quantified 24 h after treatment using a Caspase-Glo 3/7 assay (Promega), normalized to cell number."
        ),
        "statistics": (
            "Data are presented as mean +/- SD of three biological replicates. Group differences were evaluated by "
            "two-way ANOVA with Sidak's multiple comparisons test; P < 0.05 was considered significant. Analyses were "
            "performed in GraphPad Prism 10."
        ),
    }
    res = orch.execute_agent("methods_writer", {"analysis_result": methods_result, "journal_style": "cancer_research"}, {})
    data = res.data
    methods = data.get("methods_text", "") if isinstance(data, dict) else str(data)
    log("Step 6: methods_writer", tried="execute_agent('methods_writer', analysis_result=<structured protocols>)", content=methods)
    return methods

methods = step("Step 6: methods_writer", do_methods)

# ---------------------------------------------------------------------------
# Step 7: results_writer
# ---------------------------------------------------------------------------
def do_results():
    params = {
        "findings": [
            {
                "headline": f"{finding['compound']} selectively inhibits viability of KRASG12C-mutant NSCLC cells.",
                "detail": (
                    f"Across the KRASG12C-mutant lines NCI-H358, NCI-H1373, and NCI-H2122, {finding['compound']} reduced "
                    "viability with IC50 values of 4.2, 8.7, and 6.1 nM, respectively, whereas the KRAS wild-type A549 line "
                    "was insensitive (IC50 > 5 uM), indicating a >600-fold selectivity window (Fig. 1A)."
                ),
                "statistic": "P < 0.001 for mutant vs. wild-type, two-way ANOVA",
            },
            {
                "headline": f"{finding['compound']} suppresses RAF-MEK-ERK signaling.",
                "detail": (
                    "Immunoblot analysis of NCI-H358 cells treated for 4 h showed dose-dependent reduction of ERK1/2 "
                    "phosphorylation, with near-complete suppression at 100 nM, comparable to the reference inhibitor "
                    "sotorasib (Fig. 1B)."
                ),
            },
            {
                "headline": f"Pathway suppression by {finding['compound']} triggers apoptosis.",
                "detail": (
                    "Caspase-3/7 activity increased 6.8-fold after 24 h of treatment with 100 nM AZ-47, accompanied by "
                    "PARP cleavage on immunoblot; no caspase activation was observed in KRAS wild-type A549 cells (Fig. 1C)."
                ),
                "statistic": "P < 0.001 vs. vehicle",
            },
        ]
    }
    res = orch.execute_agent("results_writer", params, {})
    results = res.data
    log("Step 7: results_writer", tried="execute_agent('results_writer', findings=[{headline, detail, statistic}, ...])", content=results)
    return results

results = step("Step 7: results_writer", do_results)

# ---------------------------------------------------------------------------
# Step 8: discussion_writer
# ---------------------------------------------------------------------------
def do_discussion():
    params = {
        "principal_finding": (
            f"we show that the novel covalent inhibitor {finding['compound']} potently and selectively suppresses the "
            "viability of KRASG12C-mutant NSCLC cells, with single-digit nanomolar IC50 values and a wide selectivity "
            "window over KRAS wild-type cells."
        ),
        "interpretation": (
            "Suppression of phospho-ERK and induction of caspase-3/7 activity and PARP cleavage indicate that "
            "antiproliferative activity reflects on-target inhibition of KRASG12C signaling leading to apoptosis rather "
            "than nonspecific cytotoxicity."
        ),
        "comparison_with_literature": (
            "The cellular potency of AZ-47 is comparable to that reported for sotorasib and adagrasib in the same "
            "genetic background. As with those agents, durable pathway suppression correlated with apoptotic commitment, "
            "consistent with the view that depth of initial pathway inhibition is a determinant of clinical benefit."
        ),
        "mechanistic_insight": (
            "covalent engagement of the switch-II pocket locks KRASG12C in its inactive GDP-bound state, and the "
            "subnanomolar-to-nanomolar activity observed here suggests efficient target engagement at low drug exposures."
        ),
        "limitations": [
            "Our experiments were confined to in vitro cell line models; in vivo pharmacokinetics and efficacy remain to be established.",
            "We did not assess acquired resistance, which frequently limits first-generation G12C inhibitors.",
            "Covalent proteomics to confirm selective engagement of KRASG12C over other cysteine-containing proteins was not performed.",
        ],
        "future_directions": (
            "Future work should evaluate AZ-47 in xenograft and patient-derived models, characterize resistance "
            "mechanisms, and explore rational combinations with RTK or SHP2 inhibitors."
        ),
        "conclusion": (
            f"{finding['compound']} is a potent and selective preclinical {finding['target']} inhibitor whose cellular "
            "profile supports further development as a candidate for KRAS-mutant lung cancer."
        ),
    }
    res = orch.execute_agent("discussion_writer", params, {})
    discussion = res.data
    log("Step 8: discussion_writer", tried="execute_agent('discussion_writer', principal_finding/interpretation/limitations/...)", content=discussion)
    return discussion

discussion = step("Step 8: discussion_writer", do_discussion)

# ---------------------------------------------------------------------------
# Step 9: citation_manager with real PubMed references
# ---------------------------------------------------------------------------
def do_citations():
    # Search PubMed for real, relevant papers
    search_res = orch.execute_agent(
        "pubmed_search",
        {"query": "KRAS G12C inhibitor sotorasib adagrasib lung cancer", "max_results": 6},
        {},
    )
    papers = search_res.data.get("papers", []) if isinstance(search_res.data, dict) else []
    # second targeted search for the seminal switch-II pocket discovery
    search_res2 = orch.execute_agent(
        "pubmed_search",
        {"query": "KRAS G12C switch-II pocket Ostrem Shokat 2013", "max_results": 3},
        {},
    )
    papers2 = search_res2.data.get("papers", []) if isinstance(search_res2.data, dict) else []
    refs = papers + papers2
    # de-duplicate by PMID
    seen, unique = set(), []
    for r in refs:
        if r.get("pmid") and r["pmid"] not in seen:
            seen.add(r["pmid"])
            unique.append(r)

    cite_res = orch.execute_agent(
        "citation_manager",
        {"references": unique, "style": "vancouver"},
        {},
    )
    cdata = cite_res.data
    formatted = cdata.get("formatted_citations", []) if isinstance(cdata, dict) else []
    bibtex = cdata.get("bibtex", "") if isinstance(cdata, dict) else ""
    refs_md = "\n".join(formatted)
    log(
        "Step 9: citation_manager + pubmed_search",
        tried="pubmed_search(query='KRAS G12C inhibitor sotorasib adagrasib lung cancer') + citation_manager(references, style='vancouver')",
        content=f"[{len(unique)} unique PubMed references fetched live from NCBI E-utilities]\n\n{refs_md}",
    )
    return unique, formatted, bibtex

references, formatted_refs, bibtex_str = step("Step 9: citation_manager", do_citations)

# ---------------------------------------------------------------------------
# Step 10: compile manuscript
# ---------------------------------------------------------------------------
def do_compile():
    ref_lookup = {r.get("pmid"): i + 1 for i, r in enumerate(references)}
    manuscript = f"""# {finding['title']}

**Working draft — generated with openScience writing agents (simulated data)**

## Abstract

{abstract}

## Introduction

{introduction}

## Methods

{methods}

## Results

{results}

## Discussion

{discussion}

## References

""" + "\n".join(formatted_refs) + f"""

---

*Note: This manuscript describes a simulated research finding ({finding['compound']}) for the purpose of evaluating the openScience writing toolchain. The compound and all experimental data are fictional. References were retrieved from PubMed (NCBI E-utilities) and are real.*
"""
    (OUT / "manuscript.md").write_text(manuscript)
    (OUT / "references.bib").write_text(bibtex_str)
    (OUT / "experiment_log.json").write_text(json.dumps(LOG, indent=2))
    log("Step 10: compile manuscript", tried="Assembled sections + references -> manuscript.md; BibTeX -> references.bib", content=f"Saved to {OUT}/manuscript.md ({len(manuscript)} chars), {len(references)} references, references.bib ({len(bibtex_str)} chars)")
    return manuscript

manuscript = step("Step 10: compile manuscript", do_compile)

print("\n\n========================================")
print("EXPERIMENT COMPLETE")
print(f"Manuscript: {OUT}/manuscript.md")
print(f"BibTeX:     {OUT}/references.bib")
print(f"Log:        {OUT}/experiment_log.json")
print(f"Sections abstract={len(abstract)}w intro={len(introduction)} methods={len(methods)} results={len(results)} discussion={len(discussion)} refs={len(references)}")
