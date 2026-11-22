"""Tests for the writing skills (deterministic template engines).

Each test exercises a skill through the skill registry with real inputs and
asserts on computed values in the result dict.
"""

from __future__ import annotations

import pytest

from openscience.skills import get_skill, load_default_skills

load_default_skills()


def _run(name: str, operation: str, **kwargs):
    fn = get_skill(name)
    assert fn is not None, f"skill {name!r} not registered"
    return fn(operation=operation, **kwargs)


# ---------------------------------------------------------------------------
# text_summarization
# ---------------------------------------------------------------------------


def test_text_summarization_extractive_order_and_count():
    text = (
        "The mitochondria are essential organelles in eukaryotic cells. "
        "We measured ATP production in isolated mitochondria under hypoxia. "
        "Hypoxia reduced ATP production by 60 percent in our assays. "
        "This finding suggests a metabolic adaptation mechanism. "
        "Further work will explore downstream signaling pathways."
    )
    out = _run("text_summarization", "extractive", text=text, num_sentences=2)
    assert out["status"] == "ok"
    assert out["num_sentences"] == 2
    assert len(out["sentences"]) == 2
    # original document order must be preserved
    assert out["selected_indices"] == sorted(out["selected_indices"])
    # every selected sentence appears verbatim in the summary
    for s in out["sentences"]:
        assert s in out["summary"]
    # the high-information sentence should be selected over the trivial opener
    assert any("Hypoxia" in s for s in out["sentences"])
    assert out["word_count"] > 0


def test_text_summarization_word_limit_trim():
    text = "One two three. Four five six. Seven eight nine ten eleven twelve."
    out = _run("text_summarization", "word_limit_trim", text=text, word_limit=6)
    assert out["trimmed"] is True
    assert out["word_count"] <= 6
    assert out["text"].endswith(".")


# ---------------------------------------------------------------------------
# methodology_writing
# ---------------------------------------------------------------------------


def test_methodology_writing_render_sections():
    out = _run(
        "methodology_writing", "render",
        materials=["HeLa cells were cultured in DMEM."],
        steps=["Cells were treated with 10 uM compound for 24 h."],
        analysis=["Data were analyzed with a two-sided t-test."],
    )
    assert "Materials." in out["methods"]
    assert "Procedures." in out["methods"]
    assert "Data analysis." in out["methods"]
    assert "HeLa cells were cultured in DMEM" in out["methods"]
    assert out["sections"] == ["materials", "procedures", "analysis"]
    assert out["word_count"] > 10


def test_methodology_writing_checklist():
    text = (
        "Study design. A randomized cross-sectional cohort was used. "
        "Materials. Samples and reagents were obtained commercially. "
        "Procedures. The protocol involved incubation and centrifugation. "
        "Analysis. Statistical regression models were fit. "
        "Blinded replicate controls were used for calibration."
    )
    out = _run("methodology_writing", "checklist", text=text)
    assert out["complete"] is True
    assert out["missing"] == []
    assert set(out["present"]) == set(out["checked"])


# ---------------------------------------------------------------------------
# results_writing_ext
# ---------------------------------------------------------------------------


def test_results_writing_ext_render_with_stats():
    findings = [
        {"headline": "Tumor volume decreased by 45%",
         "detail": "compared with vehicle controls",
         "statistic": "p = 0.004"},
        "Overall survival was unchanged.",
    ]
    out = _run("results_writing_ext", "render_with_stats", findings=findings)
    assert "Tumor volume decreased by 45%" in out["paragraph"]
    assert "(p = 0.004)" in out["paragraph"]
    assert out["paragraph"].endswith(".")
    assert out["word_count"] > 5


def test_results_writing_ext_table_reference_inserter():
    text = (
        "Baseline demographics are summarized below. "
        "Outcomes were recorded at 12 months."
    )
    out = _run(
        "results_writing_ext", "table_reference_inserter",
        text=text, tables=[{"number": 1, "keyword": "demographics"}],
    )
    assert "(Table 1)" in out["text"]
    assert out["text"].index("(Table 1)") < out["text"].index("Outcomes")
    assert out["inserted"] == [1]


# ---------------------------------------------------------------------------
# discussion_writing
# ---------------------------------------------------------------------------


def test_discussion_writing_render():
    out = _run(
        "discussion_writing", "render",
        findings=["we found that compound X reduced tumor growth"],
        prior_work=["This is consistent with Smith et al. (2020)."],
        limitations=["Our sample size was modest."],
        future=["Larger cohorts are needed."],
        conclusion="compound X is a promising candidate",
    )
    d = out["discussion"]
    assert "In this study, we found that compound X reduced tumor growth." in d
    assert "prior work" in d
    assert "Our study has limitations" in d
    assert "In conclusion, compound X is a promising candidate." in d
    assert out["sections"] == ["findings", "prior_work", "limitations",
                               "implications", "conclusion"]


def test_discussion_writing_paragraph_order_check():
    good = (
        "In this study, we found a strong effect.\n\n"
        "This finding is consistent with prior work in the literature.\n\n"
        "Our study has limitations, including sample size.\n\n"
        "These results have implications for future clinical translation."
    )
    out = _run("discussion_writing", "paragraph_order_check", discussion=good)
    assert out["in_order"] is True
    assert out["detected_order"] == ["findings", "prior_work",
                                     "limitations", "implications"]


def test_discussion_writing_legacy_run():
    text = _run(
        "discussion_writing", "run",
        principal_finding="we observed a significant association",
        limitations=["The cohort was small."],
    )
    assert "In this study, we observed a significant association." in text
    assert "limitations" in text


# ---------------------------------------------------------------------------
# conclusion_writing
# ---------------------------------------------------------------------------


def test_conclusion_writing_render_and_word_count():
    out = _run(
        "conclusion_writing", "render",
        summary=["we demonstrated that X inhibits Y"],
        impact="open a new therapeutic avenue",
        future=["validate the mechanism in larger cohorts"],
    )
    assert out["conclusion"].startswith("In summary,")
    assert "open a new therapeutic avenue" in out["conclusion"]
    assert "Future work should validate the mechanism" in out["conclusion"]
    assert out["word_count"] > 5
    wc = _run("conclusion_writing", "word_count", text="one two three four")
    assert wc["word_count"] == 4


# ---------------------------------------------------------------------------
# future_work_synthesis
# ---------------------------------------------------------------------------


def test_future_work_synthesis_from_limitations():
    out = _run(
        "future_work_synthesis", "from_limitations",
        limitations=["Our study was limited by a small sample size."],
    )
    assert out["count"] == 1
    assert out["future_directions"][0].startswith("Future work should address")
    assert "small sample size" in out["future_directions"][0]
    assert out["future_directions"][0].endswith(".")


def test_future_work_synthesis_merge_dedupes():
    out = _run(
        "future_work_synthesis", "merge",
        lists=[
            ["Larger cohorts are needed.", "Longitudinal follow-up is warranted."],
            ["larger cohorts are needed."],  # duplicate (case-insensitive)
        ],
    )
    assert out["count"] == 2
    assert out["duplicates_removed"] == 1
    assert any("Longitudinal" in m for m in out["merged"])


# ---------------------------------------------------------------------------
# citation_styles
# ---------------------------------------------------------------------------

REF = {
    "authors": ["Smith, John A.", "Doe, Jane"],
    "title": "A novel therapy.",
    "journal": "Nature Medicine",
    "year": "2021",
    "doi": "10.1038/s41591-021-01234-5",
}


def test_citation_styles_format():
    out = _run("citation_styles", "format", reference=REF, style="apa")
    assert out["style"] == "apa"
    assert "(2021)" in out["citation"]
    assert "Smith" in out["citation"]
    assert "https://doi.org/10.1038/s41591-021-01234-5" in out["citation"]

    ieee = _run("citation_styles", "format", reference=REF, style="ieee")
    assert '"A novel therapy,"' in ieee["citation"]
    assert "Nature Medicine, 2021" in ieee["citation"]


def test_citation_styles_in_text_marker():
    num = _run("citation_styles", "in_text_marker", style="vancouver", number=3)
    assert num["marker"] == "[3]"
    assert num["kind"] == "numbered"
    ay = _run("citation_styles", "in_text_marker", style="apa", reference=REF)
    assert ay["kind"] == "author-year"
    assert ay["marker"] == "(Smith and Doe, 2021)"


# ---------------------------------------------------------------------------
# bibtex_parsing
# ---------------------------------------------------------------------------

BIB = """\
@article{smith2021novel,
  author = {Smith, John and Doe, Jane},
  title = {A novel {BCL2} inhibitor},
  journal = {Nature Medicine},
  year = {2021},
  doi = "10.1038/s41591-021-01234-5",
}

@book{doe2019methods,
  author = {Doe, Jane},
  title = "Methods in Biology",
  publisher = {Academic Press},
  year = 2019
}
"""


def test_bibtex_parsing_parse_and_get():
    out = _run("bibtex_parsing", "parse", text=BIB)
    assert out["count"] == 2
    first, second = out["entries"]
    assert first["entry_type"] == "article"
    assert first["key"] == "smith2021novel"
    assert first["title"] == "A novel {BCL2} inhibitor"
    assert first["year"] == "2021"
    assert second["entry_type"] == "book"
    assert second["publisher"] == "Academic Press"

    g = _run("bibtex_parsing", "get", entry=first, field="DOI")
    assert g["found"] is True
    assert g["value"] == "10.1038/s41591-021-01234-5"
    g2 = _run("bibtex_parsing", "get", entry=first, field="volume",
              default="n/a")
    assert g2["found"] is False
    assert g2["value"] == "n/a"


# ---------------------------------------------------------------------------
# citation_validation
# ---------------------------------------------------------------------------


def test_citation_validation_entry_and_report():
    ok = _run(
        "citation_validation", "validate_entry",
        entry={"authors": ["Smith J"], "title": "Title", "journal": "Nat",
               "year": "2021", "doi": "10.1038/xyz"},
    )
    assert ok["valid"] is True
    assert ok["issues"] == []

    bad = _run(
        "citation_validation", "validate_entry",
        entry={"authors": [], "title": "", "year": "3021", "doi": "abc/123"},
    )
    assert bad["valid"] is False
    assert any("missing required field: authors" in i for i in bad["issues"])
    assert any("missing required field: journal" in i for i in bad["issues"])
    assert any("implausible year" in i for i in bad["issues"])
    assert any("invalid doi format" in i for i in bad["issues"])

    report = _run(
        "citation_validation", "report",
        entries=[{"authors": ["A"], "title": "T", "journal": "J", "year": "2020"},
                 {"title": "T2"}],
    )
    assert report["total"] == 2
    assert report["valid"] == 1
    assert report["invalid"] == 1
    assert report["invalid_indices"] == [1]


# ---------------------------------------------------------------------------
# journal_templates
# ---------------------------------------------------------------------------


def test_journal_templates_get_template():
    out = _run("journal_templates", "get_template", journal="nature")
    assert out["name"] == "nature"
    assert out["sections"] == ["abstract", "introduction", "results",
                               "discussion", "methods", "references"]
    assert out["abstract_word_limit"] == 200
    assert "generic" in out["available"]


def test_journal_templates_format_check():
    manuscript = {
        "abstract": " ".join(["word"] * 250),
        "introduction": "Intro text.",
        "results": "Results text.",
        "discussion": "Discussion text.",
        "methods": "Methods text.",
        "references": "1. Ref.",
    }
    out = _run("journal_templates", "format_check", manuscript=manuscript,
               journal="nature")
    assert out["sections_missing"] == []
    assert out["sections_in_order"] is True
    assert out["abstract_word_count"] == 250
    assert any("abstract exceeds 200 words" in v for v in out["violations"])
    assert out["compliant"] is False

    missing = _run("journal_templates", "format_check",
                   manuscript={"abstract": "Short."}, journal="nature")
    assert "references" in missing["sections_missing"]


# ---------------------------------------------------------------------------
# formatting_rules
# ---------------------------------------------------------------------------


def test_formatting_rules_heading_case():
    out = _run(
        "formatting_rules", "check_heading_case",
        headings=["Results and Discussion", "methods and materials"],
    )
    assert out["checked"] == 2
    assert out["valid"] == 1
    assert out["compliant"] is False
    assert out["violations"][0]["heading"] == "methods and materials"
    assert out["violations"][0]["suggestion"] == "Methods and Materials"


def test_formatting_rules_figure_refs():
    text = (
        "As shown in Figure 1, expression increased. "
        "Figure 1. Expression levels by condition. "
        "Figure 2 shows the control; no caption exists for it."
    )
    out = _run("formatting_rules", "check_figure_refs", text=text)
    assert 1 in out["references"]
    assert 2 in out["missing_captions"]
    assert out["compliant"] is False


def test_formatting_rules_abbrev_defined():
    text = (
        "Adenosine triphosphate (ATP) was measured. ATP drives cell growth. "
        "DNA was extracted."  # DNA undefined but common? must flag
    )
    out = _run("formatting_rules", "check_abbrev_defined", text=text)
    assert out["defined"] == ["ATP"]
    assert "ATP" not in out["undefined"]
    assert "DNA" in out["undefined"]
    assert out["compliant"] is False


# ---------------------------------------------------------------------------
# letter_writing
# ---------------------------------------------------------------------------


def test_letter_writing_cover_letter():
    out = _run(
        "letter_writing", "render_cover_letter",
        title="Compound X inhibits tumor growth",
        journal="Nature Medicine",
        findings=["compound X reduced tumor volume by 45%"],
        why="This work matters because it opens a new therapeutic avenue.",
    )
    letter = out["letter"]
    assert 'Dear Dr. Editor,' in letter
    assert '"Compound X inhibits tumor growth"' in letter
    assert "Nature Medicine" in letter
    assert "compound X reduced tumor volume by 45%" in letter
    assert "has not been published previously" in letter


def test_letter_writing_rebuttal_opening():
    out = _run(
        "letter_writing", "render_rebuttal_opening",
        manuscript_id="NM-2021-1234",
    )
    assert "NM-2021-1234" in out["letter"]
    assert "point-by-point responses" in out["letter"]
    assert "Thank you" in out["letter"]


# ---------------------------------------------------------------------------
# submission_guidelines
# ---------------------------------------------------------------------------


def test_submission_guidelines_word_limit_check():
    text = " ".join(["word"] * 120)
    out = _run("submission_guidelines", "word_limit_check", text=text,
               word_limit=100)
    assert out["word_count"] == 120
    assert out["over_by"] == 20
    assert out["compliant"] is False


def test_submission_guidelines_section_requirements():
    manuscript = {"abstract": "A.", "introduction": "I.", "methods": "M."}
    out = _run(
        "submission_guidelines", "section_requirements",
        manuscript=manuscript,
        required=["abstract", "introduction", "methods", "results"],
        optional=["acknowledgements"],
    )
    assert out["missing"] == ["results"]
    assert out["compliant"] is False
    assert out["present_optional"] == []


def test_submission_guidelines_figure_count_check():
    text = "Figure 1: A. Figure 2: B. Table 1: C."
    out = _run("submission_guidelines", "figure_count_check",
               manuscript=text, max_figures=1, max_tables=1)
    assert out["figure_count"] == 2
    assert out["table_count"] == 1
    assert any("too many figures" in v for v in out["violations"])
    assert out["compliant"] is False


# ---------------------------------------------------------------------------
# response_writing
# ---------------------------------------------------------------------------


def test_response_writing_point_by_point():
    out = _run(
        "response_writing", "point_by_point",
        comments=[{"comment": "The sample size is too small.",
                   "change": "We added a power analysis"},
                  "Figure 2 is unclear."],
    )
    assert out["count"] == 2
    first = out["items"][0]
    assert first["number"] == 1
    assert "sample size" in first["comment"]
    assert "We added a power analysis" in first["change"]
    assert "reviewer's concern" in first["justification"]
    second = out["items"][1]
    assert "revised the manuscript" in second["response"]


def test_response_writing_summary_letter():
    out = _run(
        "response_writing", "summary_letter",
        changes=["Added a power analysis", "Revised Figure 2"],
        manuscript_id="NM-2021-1234",
    )
    assert "NM-2021-1234" in out["letter"]
    assert "Added a power analysis" in out["letter"]
    assert "Revised Figure 2" in out["letter"]
    assert out["count"] == 2


def test_all_skills_registered():
    for name in [
        "text_summarization", "methodology_writing", "results_writing_ext",
        "discussion_writing", "conclusion_writing", "future_work_synthesis",
        "citation_styles", "bibtex_parsing", "citation_validation",
        "journal_templates", "formatting_rules", "letter_writing",
        "submission_guidelines", "response_writing",
    ]:
        assert get_skill(name) is not None, name
