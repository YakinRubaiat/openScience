"""Tests for literature connectors and skills.

All parsing/aggregation tests are offline, using small embedded fixtures.
Network wrappers are only asserted to raise RuntimeError when the network
fails (urllib.request.urlopen is mocked to raise OSError).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from openscience.connectors.papers import biorxiv, clinicaltrials, crossref, openalex, pmc
from openscience.skills import get_skill, list_skills
from openscience.skills.literature import (  # noqa: F401 - self-register on import
    bibliometrics,
    citation_extract,
    citation_graph_skill,
    clinical_trials_skill,
    clustering,
    fact_check,
    fulltext,
    graph_viz,
    net_analysis,
    openalex_skill,
    patent_parser,
    patents_api,
    pmc_skill,
    prisma,
    pubmed_skill,
    rss,
    s2_skill,
    screening,
    similarity,
    topic_modeling_lit,
    trends,
    trial_parser,
)

# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

OPENALEX_WORK = {
    "id": "https://openalex.org/W123",
    "doi": "https://doi.org/10.1000/xyz",
    "title": "Deep learning for proteins",
    "publication_year": 2023,
    "cited_by_count": 42,
    "primary_location": {"source": {"display_name": "Nature Methods"}},
    "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
    "abstract_inverted_index": {"We": [0], "present": [1], "a": [2], "method": [3]},
}

CROSSREF_ITEM = {
    "DOI": "10.1000/abc",
    "title": ["A Crossref paper"],
    "author": [{"given": "Grace", "family": "Hopper"}],
    "container-title": ["J. Testing"],
    "issued": {"date-parts": [[2021, 5, 4]]},
}

BIORXIV_RECORD = {
    "doi": "10.1101/2020.01.01.000001",
    "title": "Preprint title",
    "authors": "Smith J; Doe J",
    "category": "bioinformatics",
    "date": "2020-01-02",
}

RSS_XML = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Feed</title>
<item><title>Paper One</title><link>http://x/1</link>
<description>About viruses</description><pubDate>Mon, 01 Jun 2020 00:00:00 +0000</pubDate></item>
<item><title>Paper Two</title><link>http://x/2</link>
<description>About proteins</description><pubDate>Tue, 02 Jun 2020 00:00:00 +0000</pubDate></item>
</channel></rss>"""

ATOM_XML = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Atom Entry</title><link href="http://x/a"/>
<summary>Atom summary</summary><published>2021-03-01T00:00:00Z</published><id>urn:1</id></entry>
</feed>"""

CT_STUDY = {
    "protocolSection": {
        "identificationModule": {"nctId": "NCT00000001", "briefTitle": "Trial A"},
        "statusModule": {"overallStatus": "RECRUITING"},
        "designModule": {"phases": ["PHASE2"], "enrollmentInfo": {"count": 120}},
        "conditionsModule": {"conditions": ["Diabetes"]},
        "armsInterventionsModule": {
            "interventions": [{"name": "Drug X", "type": "DRUG"}],
            "armGroups": [{"label": "Arm 1", "type": "Experimental"}],
        },
        "eligibilityModule": {
            "eligibilityCriteria": "Adults only",
            "sex": "ALL",
            "minimumAge": "18 Years",
        },
    }
}

JATS_XML = """<article>
<front><article-meta>
<title-group><article-title>JATS Test Article</article-title></title-group>
<abstract><p>We study important things.</p></abstract>
</article-meta></front>
<body>
<sec><title>Methods</title><p>We did the experiment.</p></sec>
<sec><title>Results</title><p>It worked well.</p></sec>
</body>
<back><ref-list><ref id="r1"/><ref id="r2"/><ref id="r3"/></ref-list>
<fig><label>Figure 1</label><caption><p>A figure caption.</p></caption></fig>
</back>
</article>"""

PATENT = {
    "publication_number": "US1234567B2",
    "title": "Test Patent",
    "assignee": "Acme Corp",
    "inventors": ["Doe, Jane"],
    "filing_date": "2020-01-15",
    "claims": ["claim one", "claim two"],
    "citations": ["US999A", "US888B"],
}

# --------------------------------------------------------------------------
# Connectors: pure parsing
# --------------------------------------------------------------------------


def test_openalex_reconstruct_abstract():
    inv = {"Hello": [0, 3], "world.": [1], "again": [2]}
    assert openalex.reconstruct_abstract(inv) == "Hello world. again Hello"
    assert openalex.reconstruct_abstract(None) == ""


def test_openalex_parse_work():
    w = openalex.parse_work(OPENALEX_WORK)
    assert w["openalex_id"] == "https://openalex.org/W123"
    assert w["doi"] == "10.1000/xyz"
    assert w["authors"] == ["Ada Lovelace"]
    assert w["cited_by_count"] == 42
    assert w["source"] == "Nature Methods"
    assert w["abstract"] == "We present a method"


def test_crossref_parse_item():
    item = crossref.parse_item(CROSSREF_ITEM)
    assert item["doi"] == "10.1000/abc"
    assert item["title"] == "A Crossref paper"
    assert item["authors"] == ["Grace Hopper"]
    assert item["year"] == 2021
    assert item["container"] == "J. Testing"
    assert item["published"] == "2021-05-04"


def test_biorxiv_parse_record():
    r = biorxiv.parse_record(BIORXIV_RECORD)
    assert r["category"] == "bioinformatics"
    assert r["date"] == "2020-01-02"


def test_biorxiv_parse_rss():
    entries = biorxiv.parse_rss(RSS_XML)
    assert len(entries) == 2
    assert entries[0]["title"] == "Paper One"
    assert entries[1]["description"] == "About proteins"


def test_biorxiv_parse_rss_atom():
    entries = biorxiv.parse_rss(ATOM_XML)
    assert len(entries) == 1
    assert entries[0]["title"] == "Atom Entry"
    assert entries[0]["link"] == "http://x/a"


def test_clinicaltrials_parse_study():
    s = clinicaltrials.parse_study(CT_STUDY)
    assert s["nct_id"] == "NCT00000001"
    assert s["status"] == "RECRUITING"
    assert s["phase"] == "PHASE2"
    assert s["conditions"] == ["Diabetes"]
    assert s["interventions"] == ["Drug X"]
    assert s["enrollment"] == 120


def test_pmc_parse_fulltext():
    out = pmc.parse_fulltext(JATS_XML)
    assert out["title"] == "JATS Test Article"
    assert "important things" in out["abstract_text"]
    headings = [s["heading"] for s in out["sections"]]
    assert "Methods" in headings and "Results" in headings
    assert out["refs_count"] == 3


# --------------------------------------------------------------------------
# Connectors: network wrappers raise RuntimeError offline
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mod,call",
    [
        (openalex, lambda m: m.search_works("protein")),
        (crossref, lambda m: m.works("protein")),
        (crossref, lambda m: m.get_work("10.1000/abc")),
        (biorxiv, lambda m: m.fetch_details("biorxiv", "2020-01-01", "2020-01-02")),
        (clinicaltrials, lambda m: m.search("diabetes")),
        (pmc, lambda m: m.search("cancer")),
        (pmc, lambda m: m.fetch_fulltext_xml("PMC12345")),
    ],
)
def test_network_wrappers_raise_runtimeerror_offline(mod, call):
    """With urlopen raising OSError, wrappers must raise RuntimeError."""
    with patch.object(mod, "urlopen", side_effect=OSError("offline")):
        with pytest.raises(RuntimeError, match="request failed"):
            call(mod)


# --------------------------------------------------------------------------
# Skills: registration
# --------------------------------------------------------------------------


def test_all_literature_skills_registered():
    names = [
        "pubmed_api", "openalex_api", "crossref_api", "biorxiv_api", "rss_parsing",
        "clinicaltrials_api", "trial_parser", "patent_api", "patent_parser",
        "pmc_api", "fulltext_parser", "semantic_scholar_api", "citation_extraction",
        "bibliometric_analysis", "paper_clustering", "semantic_similarity",
        "citation_graph", "graph_visualization", "network_analysis",
        "prisma_workflow", "screening_automation", "topic_modeling_lit",
        "trend_detection", "fact_verification",
    ]
    for n in names:
        assert n in list_skills()
        assert callable(get_skill(n))


# --------------------------------------------------------------------------
# Skills: pure operations
# --------------------------------------------------------------------------


def test_openalex_skill_parse_only():
    skill = get_skill("openalex_api")
    r = skill(operation="parse_only", work=OPENALEX_WORK)
    assert r["status"] == "ok"
    assert r["work"]["year"] == 2023


def test_openalex_skill_works_from_dict():
    skill = get_skill("openalex_api")
    r = skill(operation="works_from_dict", response={"results": [OPENALEX_WORK, OPENALEX_WORK]})
    assert r["count"] == 2


def test_crossref_skill_parse_only():
    r = get_skill("crossref_api")(operation="parse_only", item=CROSSREF_ITEM)
    assert r["item"]["doi"] == "10.1000/abc"


def test_biorxiv_skill_parse_only():
    r = get_skill("biorxiv_api")(operation="parse_only", record=BIORXIV_RECORD)
    assert r["record"]["doi"].startswith("10.1101")


def test_rss_parse_and_filter():
    skill = get_skill("rss_parsing")
    r = skill(operation="parse", xml=RSS_XML)
    assert r["count"] == 2
    f = skill(operation="filter_keywords", entries=r["entries"], keywords=["virus"])
    assert f["count"] == 1
    assert f["entries"][0]["title"] == "Paper One"


def test_clinicaltrials_skill_summarize():
    skill = get_skill("clinicaltrials_api")
    parsed = skill(operation="parse_only", study=CT_STUDY)["study"]
    r = skill(operation="summarize", studies=[parsed, parsed])
    assert r["by_phase"] == {"PHASE2": 2}
    assert r["by_status"] == {"RECRUITING": 2}


def test_trial_parser_ops():
    skill = get_skill("trial_parser")
    flat = skill(operation="parse", study=CT_STUDY)["flat"]
    assert flat["nct_id"] == "NCT00000001"
    assert flat["enrollment"] == 120
    arms = skill(operation="arms_table", study=CT_STUDY)
    assert arms["count"] == 2  # 1 arm group + 1 intervention
    elig = skill(operation="eligibility_extract", study=CT_STUDY)
    assert elig["sex"] == "ALL"
    assert "Adults" in elig["criteria"]


def test_patent_skills():
    p = get_skill("patent_api")(operation="parse_only", patent=PATENT)
    assert p["patent"]["patent_id"] == "US1234567B2"
    skill = get_skill("patent_parser")
    f = skill(operation="parse", patent=PATENT)["fields"]
    assert f["n_claims"] == 2 and f["n_citations"] == 2
    assert skill(operation="claims_extract", patent=PATENT)["claims"] == ["claim one", "claim two"]
    assert skill(operation="citations_extract", patent=PATENT)["citations"] == ["US999A", "US888B"]


def test_pmc_skill_parse_only():
    r = get_skill("pmc_api")(operation="parse_only", xml=JATS_XML)
    assert r["refs_count"] == 3


def test_fulltext_parser_skill():
    skill = get_skill("fulltext_parser")
    r = skill(operation="parse_jats", xml=JATS_XML)
    assert r["title"] == "JATS Test Article"
    m = skill(operation="extract_methods_section", xml=JATS_XML)
    assert "experiment" in m["methods_text"]
    f = skill(operation="extract_fig_legends", xml=JATS_XML)
    assert f["count"] == 1
    assert f["legends"][0]["label"] == "Figure 1"


def test_s2_skill_parse_only():
    r = get_skill("semantic_scholar_api")(
        operation="parse_only",
        paper={
            "paperId": "abc",
            "title": "S2 paper",
            "year": 2019,
            "authors": [{"name": "Turing"}],
            "citationCount": 7,
            "externalIds": {"DOI": "10.1/x"},
        },
    )
    assert r["paper"]["authors"] == ["Turing"]
    assert r["paper"]["external_ids"]["DOI"] == "10.1/x"


def test_citation_extraction():
    skill = get_skill("citation_extraction")
    text = "See 10.1000/xyz and PMID: 12345678 (Smith et al., 2019)."
    r = skill(operation="from_text", text=text)
    assert r["dois"] == ["10.1000/xyz"]
    assert r["pmids"] == ["12345678"]
    assert r["author_years"][0]["year"] == "2019"
    ref = skill(operation="to_reference_dict", doi="10.1/x", title="T", author="Doe J")
    assert ref["reference"]["authors"] == ["Doe J"]


def test_bibliometrics():
    skill = get_skill("bibliometric_analysis")
    papers = [
        {"year": 2020, "journal": "J1", "authors": ["A", "B"]},
        {"year": 2020, "journal": "J1", "authors": ["A"]},
        {"year": 2021, "journal": "J2", "authors": ["C"]},
    ]
    assert skill(operation="counts_by_year", papers=papers)["counts_by_year"] == {"2020": 2, "2021": 1}
    top = skill(operation="top_journals", papers=papers)["top_journals"]
    assert top[0] == {"journal": "J1", "count": 2}
    auth = skill(operation="top_authors", papers=papers)["top_authors"]
    assert auth[0] == {"author": "A", "count": 2}
    assert skill(operation="h_index", citations=[10, 8, 5, 4, 3])["h_index"] == 4
    assert skill(operation="h_index", citations=[])["h_index"] == 0


def test_paper_clustering_separates_two_clusters():
    skill = get_skill("paper_clustering")
    docs = [
        "protein folding structure alpha helix",
        "protein structure folding beta sheet",
        "climate change warming atmosphere carbon",
        "global warming climate carbon emissions",
    ]
    r = skill(operation="tfidf_kmeans", documents=docs, n_clusters=2)
    assert r["n_clusters"] == 2
    labels = r["labels"]
    assert labels[0] == labels[1]
    assert labels[2] == labels[3]
    assert labels[0] != labels[2]
    s = skill(operation="summarize_clusters", documents=docs, labels=labels)
    assert set(s["clusters"].keys()) == {str(labels[0]), str(labels[2])}


def test_semantic_similarity():
    skill = get_skill("semantic_similarity")
    docs = ["cat sits on mat", "quantum computing qubits", "cat on the mat"]
    r = skill(operation="tfidf_cosine", query="cat mat", documents=docs)
    assert len(r["scores"]) == 3
    assert r["scores"][0] > 0.4
    top = skill(operation="top_k_similar", query="cat mat", documents=docs, k=1)
    assert top["top"][0]["index"] in (0, 2)


def test_citation_graph():
    skill = get_skill("citation_graph")
    papers = [
        {"paper_id": "A", "references": ["B", "C"]},
        {"paper_id": "B", "references": ["C"]},
        {"paper_id": "C", "references": []},
    ]
    b = skill(operation="build", papers=papers)
    assert b["n_edges"] == 3
    counts = skill(operation="citation_counts", papers=papers)["counts"]
    assert counts == {"B": 1, "C": 2}
    cent = skill(operation="centrality", papers=papers)["centrality"]
    # C has the highest in-degree centrality
    assert max(cent, key=cent.get) == "C"


def test_graph_viz():
    skill = get_skill("graph_visualization")
    nodes = ["A", "B", "C"]
    edges = [["A", "B"], ["B", "C"]]
    coords = skill(operation="spring_layout_coords", nodes=nodes, edges=edges)["coords"]
    assert set(coords) == {"A", "B", "C"}
    assert all(len(v) == 2 for v in coords.values())
    png = skill(operation="draw", nodes=nodes, edges=edges)["png_base64"]
    assert isinstance(png, str) and len(png) > 100
    g = skill(operation="to_gephi_csv", nodes=nodes, edges=edges)
    assert "A,B" in g["edges_csv"]
    assert g["nodes_csv"].splitlines()[0] == "Id,Label"


def test_network_analysis():
    skill = get_skill("network_analysis")
    nodes = ["A", "B", "C", "D", "E"]
    edges = [["A", "B"], ["B", "C"], ["D", "E"]]
    dist = skill(operation="degree_dist", nodes=nodes, edges=edges)["distribution"]
    assert dist == {"1": 4, "2": 1}
    comps = skill(operation="connected_components", nodes=nodes, edges=edges)
    assert comps["n_components"] == 2
    assert comps["components"][0] == ["A", "B", "C"]
    top = skill(operation="betweenness_top", nodes=nodes, edges=edges, k=1)
    if top["top"]:  # requires networkx
        assert top["top"][0]["node"] == "B"


def test_prisma():
    skill = get_skill("prisma_workflow")
    counts = skill(operation="flow_counts", identified=100, screened=40, included=10)
    assert counts["exclusions"]["identified_to_screened_excluded"] == 60
    ok = skill(operation="validate", identified=100, screened=40, included=10)
    assert ok["valid"] is True
    bad = skill(operation="validate", identified=10, screened=40, included=60)
    assert bad["valid"] is False
    assert any("screened" in e for e in bad["errors"])
    neg = skill(operation="validate", identified=-5)
    assert neg["valid"] is False
    diagram = skill(operation="diagram_text", identified=100, screened=40)["diagram"]
    assert "n = 100" in diagram and "excluded: 60" in diagram


def test_screening():
    skill = get_skill("screening_automation")
    papers = [
        {"title": "Drug trial", "abstract": "randomized controlled trial", "doi": "10.1/a"},
        {"title": "Rat study", "abstract": "in mice only", "doi": "10.1/b"},
        {"title": "Drug trial", "abstract": "duplicate", "doi": "10.1/a"},
        {"title": "Opinion", "abstract": "no data"},
    ]
    s = skill(
        operation="keyword_screen",
        papers=papers,
        include_patterns=[r"randomized|trial"],
        exclude_patterns=[r"mice|rat"],
    )
    decisions = [x["decision"] for x in s["screened"]]
    assert decisions == ["include", "exclude", "include", "uncertain"]
    d = skill(operation="dedupe", papers=papers)
    assert d["n_duplicates"] == 1
    assert len(d["papers"]) == 3
    samp = skill(operation="sample_for_review", papers=papers, n=2, seed=1)
    assert samp["count"] == 2


def test_topic_modeling_lit():
    skill = get_skill("topic_modeling_lit")
    docs = [
        "protein folding structure", "protein structure helix",
        "climate carbon warming", "climate warming atmosphere",
    ]
    r = skill(operation="nmf_topics", documents=docs, n_topics=2, top_n=3)
    assert r["n_topics"] == 2
    all_terms = [t for topic in r["topics"] for t in topic["terms"]]
    assert any("protein" in t or "climate" in t for t in all_terms)
    m = skill(operation="doc_topic_matrix", documents=docs, n_topics=2)["matrix"]
    assert len(m) == 4 and all(len(row) == 2 for row in m)
    tt = skill(operation="top_terms", documents=docs, top_n=3)["terms"]
    assert len(tt) == 3


def test_trend_detection():
    skill = get_skill("trend_detection")
    papers = [
        {"year": 2018, "terms": ["microscopy"]},
        {"year": 2019, "terms": ["microscopy"]},
        {"year": 2021, "terms": ["crispr"]},
        {"year": 2022, "terms": ["crispr", "crispr"]},
        {"year": 2022, "terms": ["crispr"]},
    ]
    counts = skill(operation="by_year_counts", papers=papers)["counts"]
    assert counts == {"2018": 1, "2019": 1, "2021": 1, "2022": 2}
    em = skill(operation="emerging_terms", papers=papers, split_year=2020)["terms"]
    assert em[0]["term"] == "crispr"
    gr = skill(operation="growth_rate", counts={"2018": 10, "2022": 40})
    assert gr["growth_rate"] == pytest.approx((40 / 10) ** 0.25 - 1, abs=1e-4)


def test_fact_verification():
    skill = get_skill("fact_verification")
    r = skill(
        operation="claim_vs_abstract_rules",
        claim="Aspirin reduces fever",
        abstract="Aspirin reduces fever in adults significantly",
    )
    assert r["verdict"] == "supported"
    assert r["score"] > 0.3
    neg = skill(
        operation="claim_vs_abstract_rules",
        claim="Aspirin reduces fever",
        abstract="We found aspirin did not reduce fever in our cohort",
    )
    assert neg["abstract_negation"] is True
    rep = skill(
        operation="report_table",
        claim="Aspirin reduces fever",
        papers=[
            {"title": "P1", "abstract": "Aspirin reduces fever"},
            {"title": "P2", "abstract": "Unrelated topic entirely"},
        ],
    )
    assert rep["count"] == 2
    assert rep["rows"][0]["verdict"] == "supported"


# --------------------------------------------------------------------------
# Skills: unknown ops raise ValueError
# --------------------------------------------------------------------------


def test_unknown_operation_raises():
    with pytest.raises(ValueError, match="Unknown operation"):
        get_skill("bibliometric_analysis")(operation="nonsense")
