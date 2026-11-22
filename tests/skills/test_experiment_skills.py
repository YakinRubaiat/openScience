"""Tests for the experiment skills package."""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest

from openscience.skills import execute_skill, get_skill
from openscience.skills.experiment import (  # noqa: F401 - ensures registration
    backup_manager,
    database_writer,
    metadata_extractor,
    metadata_standards,
    preregistration,
    sample_size,
    s3_manager,
    study_design_doc,
    validation_rules,
    version_controller,
)

SKILLS = [
    "metadata_standards",
    "validation_rules",
    "sample_size_calc",
    "preregistration_templates",
    "study_design_documentation",
    "metadata_extractor",
    "database_writer",
    "s3_manager",
    "version_controller",
    "backup_manager",
]


def test_all_skills_registered():
    for name in SKILLS:
        assert get_skill(name) is not None, f"{name} not registered"


# ---------------------------------------------------------------- metadata_standards


def test_mininfo_missing_fields_detected():
    r = execute_skill("metadata_standards", "validate_mininfo", metadata={
        "title": "My experiment",
        "summary": "A test",
    })
    assert r["status"] == "ok"
    assert r["valid"] is False
    assert "organism" in r["missing_fields"]
    assert "instrument_model" in r["missing_fields"]
    assert "title" in r["present_fields"]
    assert set(r["missing_fields"]) | set(r["present_fields"]) == set(
        r["present_fields"] + r["missing_fields"]
    )


def test_mininfo_complete_metadata_valid():
    template = execute_skill("metadata_standards", "template", include_optional=False)["template"]
    meta = {k: "x" for k in template}
    r = execute_skill("metadata_standards", "validate_mininfo", metadata=meta)
    assert r["valid"] is True
    assert r["missing_fields"] == []


def test_mininfo_empty_value_flagged():
    template = execute_skill("metadata_standards", "template", include_optional=False)["template"]
    meta = {k: "x" for k in template}
    meta["summary"] = "   "
    r = execute_skill("metadata_standards", "validate_mininfo", metadata=meta)
    assert r["valid"] is False
    assert "summary" in r["empty_fields"]


def test_suggest_fields_and_template():
    r = execute_skill("metadata_standards", "suggest_fields", metadata={"title": "x"})
    suggested = {f["field"] for f in r["suggested_required"]}
    assert "organism" in suggested
    assert "title" not in suggested

    t = execute_skill("metadata_standards", "template")
    assert "organism" in t["template"]
    assert "keywords" in t["template"]  # optional included by default


# ---------------------------------------------------------------- validation_rules


def test_validation_required():
    data = [{"id": 1, "name": "a"}, {"id": 2, "name": ""}]
    r = execute_skill("validation_rules", "required", data=data, fields=["id", "name"])
    assert r["valid"] is False
    assert r["n_violations"] == 1
    assert r["violations"][0]["field"] == "name"


def test_validation_types_and_ranges():
    data = [{"age": 30, "score": 0.5}, {"age": 400, "score": "high"}]
    r = execute_skill(
        "validation_rules",
        "types",
        data=data,
        schema={"age": "int", "score": "float"},
    )
    assert r["n_violations"] == 1  # second score is a str

    r = execute_skill(
        "validation_rules",
        "ranges",
        data=data,
        rules={"age": {"min": 0, "max": 120}},
    )
    assert r["n_violations"] == 1
    assert r["violations"][0]["row"] == 1


def test_validation_regex_and_report():
    data = [{"code": "AB-123"}, {"code": "not-a-code"}]
    r = execute_skill(
        "validation_rules",
        "regex_rule",
        data=data,
        column="code",
        pattern=r"[A-Z]{2}-\d{3}",
    )
    assert r["n_violations"] == 1

    rep = execute_skill(
        "validation_rules",
        "report",
        data=data,
        required_fields=["code"],
        regex_rules={"code": r"[A-Z]{2}-\d{3}"},
    )
    assert rep["valid"] is False
    assert rep["n_violations"] == 1
    assert "required" in rep["checks"] and "regex" in rep["checks"]


# ---------------------------------------------------------------- sample_size_calc


def test_two_means_power_case():
    # Classic case: Cohen's d = 0.5, alpha=0.05 two-sided, power=0.8 -> n ≈ 64/group
    r = execute_skill(
        "sample_size_calc", "two_means", effect_size=0.5, alpha=0.05, power=0.8
    )
    assert abs(r["n_per_group"] - 64) <= 1
    assert r["n_total"] == 2 * r["n_per_group"]


def test_two_means_from_means_and_sd():
    r = execute_skill("sample_size_calc", "two_means", mean1=10, mean2=12, sd=4)
    assert r["effect_size"] == pytest.approx(0.5)
    assert abs(r["n_per_group"] - 64) <= 1


def test_two_proportions():
    r = execute_skill("sample_size_calc", "two_proportions", p1=0.5, p2=0.65)
    assert r["n_per_group"] > 50  # sanity; exact value ~93
    assert r["effect_metric"] == "Cohen's h"


def test_survival_freedman():
    # Freedman: hr=0.5, p_event=0.8, alpha=0.05 (two-sided), power=0.8
    # E = (1.96+0.8416)^2 * (1*0.5+1)^2 / (1*(0.5-1)^2)
    #   = 7.849 * 2.25 / 0.25 = 70.6 -> 71 events; total = 71/0.8 -> 89
    r = execute_skill(
        "sample_size_calc", "survival", hr=0.5, p_event=0.8, alpha=0.05, power=0.8
    )
    assert abs(r["n_events_required"] - 71) <= 1
    assert abs(r["n_total"] - 89) <= 2


def test_correlation():
    # n = ((1.96+0.8416)/atanh(0.3))^2 + 3 ~ 84.3 -> 85
    r = execute_skill("sample_size_calc", "correlation", r=0.3, alpha=0.05, power=0.8)
    assert abs(r["n_total"] - 85) <= 1


# ---------------------------------------------------------------- preregistration_templates


def test_preregistration_render():
    r = execute_skill(
        "preregistration_templates",
        "render",
        title="Sleep & Memory",
        hypotheses=["H1: sleep improves recall", "H2: naps help"],
        design={"type": "between", "groups": ["nap", "no-nap"]},
        analysis_plan=["two-sample t-test on recall score"],
    )
    md = r["markdown"]
    assert "# Preregistration: Sleep & Memory" in md
    assert "1. H1: sleep improves recall" in md
    assert "two-sample t-test" in md
    assert "## Study Design" in md


def test_aspredicted_format():
    r = execute_skill(
        "preregistration_templates",
        "aspredicted_format",
        title="Study X",
        hypothesis="Something",
    )
    assert r["markdown"].count("## ") == 8  # all 8 AsPredicted questions rendered
    assert "What's the main question" in r["markdown"]


def test_preregistration_checklist():
    r = execute_skill(
        "preregistration_templates", "checklist", completed=["title", "hypotheses"]
    )
    assert r["complete"] is False
    assert "analysis_plan" in r["missing"]
    assert r["n_completed"] == 2


# ---------------------------------------------------------------- study_design_documentation


def test_describe_design():
    r = execute_skill(
        "study_design_documentation",
        "describe_design",
        design_type="mixed",
        factors={"group": ["a", "b"], "time": ["pre", "post", "followup"]},
        randomization="block",
    )
    assert r["design_type"] == "mixed"
    assert r["n_factorial_cells"] == 6
    assert len(r["factors"]) == 2

    with pytest.raises(ValueError):
        execute_skill("study_design_documentation", "describe_design", design_type="bogus")


def test_variables_table():
    r = execute_skill(
        "study_design_documentation",
        "variables_table",
        variables=[
            {"name": "treatment", "type": "independent", "levels_or_range": "A/B"},
            {"name": "recall", "type": "dependent", "measurement": "score 0-100"},
        ],
    )
    assert "| treatment | independent |" in r["markdown"]
    assert r["n_variables"] == 2


def test_consort_diagram_text():
    r = execute_skill(
        "study_design_documentation",
        "consort_diagram_text",
        enrolled=200,
        assessed=190,
        excluded=10,
        allocated={"treatment": 80, "control": 80},
        lost_to_followup={"treatment": 5},
        analyzed={"treatment": 75, "control": 78},
    )
    assert "Enrolled: 200" in r["diagram"]
    assert r["total_allocated"] == 160
    assert r["total_analyzed"] == 153


# ---------------------------------------------------------------- metadata_extractor


def test_from_filename_parses_key_value():
    r = execute_skill(
        "metadata_extractor",
        "from_filename",
        filename="sample=Patient12_group=treated_batch=3_reads.fastq.gz",
    )
    assert r["metadata"] == {"sample": "Patient12", "group": "treated", "batch": "3"}


def test_from_header(tmp_path):
    f = tmp_path / "data.tsv"
    f.write_text("id\tgroup\tscore\n1\ta\t3.2\n2\tb\t4.1\n")
    r = execute_skill("metadata_extractor", "from_header", path=str(f), n_lines=3)
    assert r["delimiter"] == "\t"
    assert r["columns"] == ["id", "group", "score"]


def test_infer_column_roles():
    data = [
        {"subject_id": "S1", "age": 25, "group": "a", "visit_date": "2024-01-01"},
        {"subject_id": "S2", "age": 31, "group": "b", "visit_date": "2024-01-02"},
    ]
    r = execute_skill("metadata_extractor", "infer_column_roles", data=data)
    roles = {k: v["role"] for k, v in r["roles"].items()}
    assert roles["subject_id"] == "id"
    assert roles["age"] == "numeric"
    assert roles["group"] == "categorical"
    assert roles["visit_date"] == "datetime"


def test_redaction_correctness():
    text = "Contact jdoe@example.com or 555-123-4567. SSN 123-45-6789."
    r = execute_skill("metadata_extractor", "redact", text=text)
    assert r["n_redacted"] == 3
    assert "jdoe@example.com" not in r["redacted_text"]
    assert "555-123-4567" not in r["redacted_text"]
    assert r["redacted_text"].count("[REDACTED]") == 3

    # selective kinds
    r2 = execute_skill("metadata_extractor", "redact", text=text, kinds=["email"])
    assert r2["n_redacted"] == 1
    assert "555-123-4567" in r2["redacted_text"]


# ---------------------------------------------------------------- database_writer


def test_sqlite_roundtrip(tmp_path):
    db = str(tmp_path / "test.db")
    records = [{"id": 1, "val": "a"}, {"id": 2, "val": "b"}]
    r = execute_skill(
        "database_writer", "to_sqlite", data=records, db_path=db, table="samples"
    )
    assert r["n_rows_written"] == 2
    assert r["n_rows_total"] == 2
    assert Path(db).exists()

    out = execute_skill("database_writer", "read_table", db_path=db, table="samples")
    assert out["n_rows"] == 2
    assert sorted(out["columns"]) == ["id", "val"]
    assert out["records"][0]["val"] == "a"


def test_upsert_stub(tmp_path):
    db = str(tmp_path / "test.db")
    execute_skill(
        "database_writer",
        "to_sqlite",
        data=[{"id": 1, "val": "a"}, {"id": 2, "val": "b"}],
        db_path=db,
        table="t",
    )
    r = execute_skill(
        "database_writer",
        "upsert_stub",
        data=[{"id": 2, "val": "B"}, {"id": 3, "val": "c"}],
        db_path=db,
        table="t",
        key_columns=["id"],
    )
    assert r["n_rows_upserted"] == 2
    out = execute_skill("database_writer", "read_table", db_path=db, table="t")
    by_id = {row["id"]: row["val"] for row in out["records"]}
    assert by_id == {1: "a", 2: "B", 3: "c"}


# ---------------------------------------------------------------- s3_manager


def test_s3_local_sync_manifest_verify(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("alpha")
    sub = src / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("beta")
    bucket = tmp_path / "bucket"

    r = execute_skill(
        "s3_manager", "local_sync", source_dir=str(src), bucket_path=str(bucket)
    )
    assert r["n_copied"] == 2
    assert r["n_synced"] == 2

    m = execute_skill("s3_manager", "manifest", directory=str(bucket))
    assert m["n_files"] == 2
    import hashlib

    assert m["files"]["a.txt"]["md5"] == hashlib.md5(b"alpha").hexdigest()
    assert m["total_bytes"] == 9

    v = execute_skill(
        "s3_manager", "verify_sync", source_dir=str(src), bucket_path=str(bucket)
    )
    assert v["verified"] is True

    # diverge: delete a file in source, resync removes it from the bucket
    (sub / "b.txt").unlink()
    r2 = execute_skill(
        "s3_manager", "local_sync", source_dir=str(src), bucket_path=str(bucket)
    )
    assert r2["n_removed"] == 1
    v2 = execute_skill(
        "s3_manager", "verify_sync", source_dir=str(src), bucket_path=str(bucket)
    )
    assert v2["verified"] is True


# ---------------------------------------------------------------- version_controller


def test_version_snapshot_diff_correctness(tmp_path):
    src = tmp_path / "data"
    src.mkdir()
    (src / "keep.txt").write_text("same")
    (src / "old.txt").write_text("v1")
    (src / "change.txt").write_text("v1")
    versions = tmp_path / "versions"

    s1 = execute_skill(
        "version_controller",
        "snapshot",
        source_dir=str(src),
        versions_dir=str(versions),
        label="first",
    )
    assert s1["manifest"]["n_files"] == 3

    # mutate: remove old.txt, add new.txt, change change.txt
    (src / "old.txt").unlink()
    (src / "new.txt").write_text("new")
    (src / "change.txt").write_text("v2")
    s2 = execute_skill(
        "version_controller",
        "snapshot",
        source_dir=str(src),
        versions_dir=str(versions),
        label="second",
    )

    d = execute_skill(
        "version_controller",
        "diff_manifests",
        versions_dir=str(versions),
        old_version=s1["version"],
        new_version=s2["version"],
    )
    assert d["added"] == ["new.txt"]
    assert d["removed"] == ["old.txt"]
    assert d["changed"] == ["change.txt"]
    assert d["identical"] is False

    log = execute_skill("version_controller", "log", versions_dir=str(versions))
    assert log["n_versions"] == 2
    assert log["log"][0]["label"] == "first"

    # manifest data written to disk as json
    with open(Path(s1["snapshot_path"]) / "manifest.json") as fh:
        assert json.load(fh)["n_files"] == 3


# ---------------------------------------------------------------- backup_manager


def test_backup_create_verify_restore(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "f1.txt").write_text("one")
    (src / "f2.txt").write_text("two")
    bdir = tmp_path / "backups"

    r = execute_skill(
        "backup_manager", "create", source_dir=str(src), backup_dir=str(bdir), backup_name="daily"
    )
    assert r["n_files"] == 2
    backup_path = Path(r["backup_path"])
    assert backup_path.exists()
    assert backup_path.suffix == ".gz"

    v = execute_skill("backup_manager", "verify", backup_path=str(backup_path))
    assert v["verified"] is True
    assert v["n_files"] == 2

    lst = execute_skill("backup_manager", "list_backups", backup_dir=str(bdir))
    assert lst["n_backups"] == 1

    target = tmp_path / "restored"
    rr = execute_skill(
        "backup_manager", "restore", backup_path=str(backup_path), target_dir=str(target)
    )
    assert rr["restored"] is True
    assert (target / "src" / "f1.txt").read_text() == "one"
    with tarfile.open(backup_path, "r:gz") as tf:
        assert all(m.name.startswith("src/") for m in tf.getmembers())
