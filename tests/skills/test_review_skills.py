"""Real-behavior tests for openscience.skills.review.

AST fallbacks are exercised on sample files with known defect densities;
subprocess-dependent operations are skipped when the binary is missing (or
exercised only through their offline parse paths).
"""

from __future__ import annotations

import json
import shutil

import pytest

from openscience.skills._common import has_module
from openscience.skills.review import (
    arch_rules,
    axe_skill,
    bandit_skill,
    black_skill,
    budget_opt,
    budget_plan,
    checkov_skill,
    cost_model,
    coverage_skill,
    darglint_skill,
    hadolint_skill,
    import_linter_skill,
    interrogate_skill,
    license_check,
    mitigation,
    mutmut_skill,
    mypy_skill,
    openapi_validator,
    pa11y_skill,
    pgbadger_skill,
    pipdeptree_skill,
    pydeps_skill,
    pydocstyle_skill,
    pylint_skill,
    pytest_skill,
    radon_skill,
    resource_planning,
    risk_analysis,
    safety_skill,
    semgrep_skill,
    spectral_skill,
    sqlfluff_skill,
    timeline,
    trivy_skill,
)

# ---------------------------------------------------------------- fixtures


@pytest.fixture
def dirty_py(tmp_path):
    """Python file with a known density of bandit-detectable issues."""
    code = (
        "import pickle\n"
        "import subprocess\n"
        "password = 'hunter2'\n"
        "\n"
        "\n"
        "def run(user_input):\n"
        "    eval(user_input)\n"
        "    exec(user_input)\n"
        "    subprocess.call(user_input, shell=True)\n"
        "    return pickle.loads(user_input)\n"
        "\n"
        "\n"
        "def check(x):\n"
        "    assert x > 0\n"
        "    return x\n"
    )
    f = tmp_path / "dirty.py"
    f.write_text(code)
    return f


@pytest.fixture
def two_module_pkg(tmp_path):
    """pkg with a -> b -> a import cycle plus a standalone module."""
    (tmp_path / "a.py").write_text("import b\nX = 1\n")
    (tmp_path / "b.py").write_text("import a\nY = 2\n")
    (tmp_path / "c.py").write_text("VALUE = 3\n")
    return tmp_path


# ------------------------------------------------------------------- bandit


def test_bandit_fallback_scan_counts(dirty_py, monkeypatch):
    monkeypatch.setattr(bandit_skill, "_bandit_available", lambda: False)
    res = bandit_skill.run("scan", path=str(dirty_py))
    assert res["engine"] == "ast-fallback"
    by_code = {}
    for issue in res["issues"]:
        by_code[issue["test_id"]] = by_code.get(issue["test_id"], 0) + 1
    assert by_code.get("B307") == 1  # eval
    assert by_code.get("B102") == 1  # exec
    assert by_code.get("B101") == 1  # assert in non-test
    assert by_code.get("B301") == 1  # pickle.loads
    assert by_code.get("B602") == 1  # shell=True
    assert by_code.get("B105") == 1  # hardcoded password
    report = bandit_skill.run("report", issues=res["issues"])
    assert report["total"] == 6
    assert report["by_severity"]["HIGH"] == 3


@pytest.mark.skipif(not has_module("bandit"), reason="bandit not installed")
def test_bandit_real_scan(dirty_py):
    res = bandit_skill.run("scan", path=str(dirty_py))
    assert res["engine"] == "bandit"
    assert res["n_issues"] >= 4  # real bandit finds eval/exec/shell/pickle-ish


# ------------------------------------------------------------------- safety


def test_safety_parse_and_check():
    content = (
        "flask==2.0.1\n"
        "requests==2.31.0\n"
        "Pillow==9.4.0  # comment\n"
        "numpy>=1.26\n"
        "-e .\n"
    )
    parsed = safety_skill.run("parse_requirements", content=content)
    assert parsed["n_requirements"] == 4
    res = safety_skill.run("check", content=content)
    flagged = {v["package"] for v in res["vulnerabilities"]}
    # flask pinned below fix, pillow below fix; requests==2.31 is safe;
    # numpy uses >= (not a fixed pin) so it is not checked
    assert flagged == {"flask", "pillow"}
    assert res["n_vulnerable"] == 2


def test_safety_check_from_file(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("django==3.2.0\n")
    res = safety_skill.run("check", path=str(req))
    assert res["n_vulnerable"] == 1
    assert res["vulnerabilities"][0]["min_safe_version"] == "4.2.0"


# ------------------------------------------------------------------ semgrep


def test_semgrep_fallback_scan(tmp_path):
    (tmp_path / "lib.py").write_text(
        "import pickle\n"
        "\n"
        "\n"
        "def debug(x):\n"
        "    print(x)\n"
        "    return eval(x)\n"
    )
    res = semgrep_skill.run("scan", path=str(tmp_path), engine="fallback")
    if res["engine"] == "semgrep":
        pytest.skip("semgrep CLI present; fallback not selected")
    ids = [f["rule_id"] for f in res["findings"]]
    assert ids.count("print-in-lib-code") == 1
    assert "dangerous-imports" in ids
    assert "dangerous-calls" in ids


def test_semgrep_list_rules():
    res = semgrep_skill.run("list_rules")
    assert res["n_rules"] >= 3
    assert {r["id"] for r in res["rules"]} >= {"dangerous-imports", "print-in-lib-code"}


def test_semgrep_custom_rules(tmp_path):
    (tmp_path / "m.py").write_text("import os\nos.system('ls')\n")
    rules = [{"id": "no-os-system", "message": "os.system", "severity": "ERROR",
              "pattern": {"kind": "call", "names": ["os.system"]}}]
    res = semgrep_skill.run("scan", path=str(tmp_path), rules=rules)
    assert res["engine"] == "ast-fallback"
    assert res["n_findings"] == 1
    assert res["findings"][0]["rule_id"] == "no-os-system"


# ------------------------------------------------------------------- pylint


def test_pylint_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(pylint_skill, "_pylint_available", lambda: False)
    code = (
        "import os\n"
        "import sys\n"
        "\n"
        "\n"
        "def helper(a):\n"
        "    unused_local = 5\n"
        "    return a + 1\n"
        "\n"
        "\n"
        "def wide(a, b, c, d, e, f, g):\n"
        "    return sys.argv and (a, b, c, d, e, f, g)\n"
    )
    f = tmp_path / "lintme.py"
    f.write_text(code)
    res = pylint_skill.run("lint", path=str(f))
    assert res["engine"] == "ast-fallback"
    symbols = [m["symbol"] for m in res["messages"]]
    assert symbols.count("unused-import") == 1  # os unused; sys used
    assert "unused-variable" in symbols
    assert symbols.count("too-many-arguments") == 1
    score = pylint_skill.run("score", messages=res["messages"])
    assert 0 <= score["score"] < 10


# -------------------------------------------------------------------- radon


def test_radon_fallback_complexity(tmp_path, monkeypatch):
    monkeypatch.setattr(radon_skill, "_radon_available", lambda: False)
    code = (
        "def flat(x):\n"
        "    return x\n"
        "\n"
        "\n"
        "def branchy(x):\n"
        "    if x > 0:\n"          # +1
        "        for i in range(3):\n"  # +1
        "            if i and x:\n"     # +1 if, +1 boolop
        "                print(i)\n"
        "    elif x < -1:\n"       # +1
        "        while x:\n"       # +1
        "            x += 1\n"
        "    else:\n"
        "        try:\n"
        "            1 / x\n"
        "        except ZeroDivisionError:\n"  # +1
        "            pass\n"
        "    return x\n"
    )
    f = tmp_path / "m.py"
    f.write_text(code)
    res = radon_skill.run("complexity", path=str(f))
    funcs = {fn["name"]: fn["complexity"] for fn in res["functions"]}
    assert funcs["flat"] == 1
    assert funcs["branchy"] == 8
    hist = radon_skill.run("cc_histogram", functions=res["functions"])
    assert hist["histogram"]["A"] == 1
    assert hist["histogram"]["B"] == 1
    mi = radon_skill.run("mi_report", path=str(f))
    assert mi["files"][0]["mi"] >= 0


# -------------------------------------------------------------------- black


def test_black_fallback_check(tmp_path, monkeypatch):
    monkeypatch.setattr(black_skill, "_black_available", lambda: False)
    messy = tmp_path / "messy.py"
    messy.write_text("def f( a ,b ):\n    return a+   b   \n")
    clean = tmp_path / "clean.py"
    clean.write_text('"""Module docstring."""\n\n\ndef f(a, b):\n    return (a, b)\n')
    res = black_skill.run("check", path=str(messy))
    assert res["engine"] == "ast-fallback"
    assert not res["all_formatted"]
    assert res["unformatted"] == [str(messy)]
    diff = black_skill.run("format_diff", path=str(messy))
    assert diff["has_changes"]
    res_clean = black_skill.run("report_unformatted", path=str(clean))
    assert res_clean["n_unformatted"] == 0


@pytest.mark.skipif(shutil.which("black") is None, reason="black CLI missing")
def test_black_real_check(tmp_path):
    messy = tmp_path / "messy.py"
    messy.write_text("def f( a ,b ):\n    return a+   b\n")
    res = black_skill.run("check", path=str(messy))
    assert res["engine"] == "black"
    assert not res["all_formatted"]


# -------------------------------------------------------------------- mypy


def test_mypy_missing_raises(tmp_path, monkeypatch):
    if has_module("mypy") or shutil.which("mypy"):
        pytest.skip("mypy installed")
    with pytest.raises(RuntimeError, match="pip install mypy"):
        mypy_skill.run("typecheck", path=str(tmp_path))


def test_mypy_annotation_coverage(tmp_path):
    code = (
        "def typed(a: int, b: str) -> int:\n"
        "    return a\n"
        "\n"
        "\n"
        "def half_typed(a: int, b) -> int:\n"
        "    return a\n"
        "\n"
        "\n"
        "def untyped(a, b):\n"
        "    return a\n"
    )
    f = tmp_path / "ann.py"
    f.write_text(code)
    res = mypy_skill.run("count_annotated_functions", path=str(f))
    assert res["n_functions"] == 3
    assert res["n_annotated"] == 1
    assert res["coverage_percent"] == pytest.approx(33.33)


# -------------------------------------------------------------- pydocstyle


def test_pydocstyle_check(tmp_path):
    code = (
        '"""Module doc."""\n'
        "\n"
        "\n"
        "class Documented:\n"
        '    """A class."""\n'
        "\n"
        "\n"
        "class Undocumented:\n"
        "    pass\n"
        "\n"
        "\n"
        "def with_doc():\n"
        '    """Doc."""\n'
        "\n"
        "\n"
        "def without_doc():\n"
        "    return 1\n"
        "\n"
        "\n"
        "def _private():\n"
        "    return 2\n"
    )
    f = tmp_path / "docs.py"
    f.write_text(code)
    res = pydocstyle_skill.run("check", path=str(f))
    missing_names = {(v["kind"], v["name"]) for v in res["violations"]}
    assert missing_names == {("class", "Undocumented"), ("function", "without_doc")}
    cov = pydocstyle_skill.run("coverage_percent", path=str(f))
    # 5 public objects (module, 2 classes, 2 functions), 3 documented
    assert cov["documented"] == 3
    assert cov["total"] == 5
    assert cov["coverage_percent"] == 60.0
    misses = pydocstyle_skill.run("missing_list", path=str(f))
    assert misses["n_missing"] == 2


# ----------------------------------------------------------------- darglint


def test_darglint_param_check(tmp_path):
    code = (
        'def good(a, b):\n'
        '    """Do it.\n'
        "\n"
        "    Args:\n"
        "        a: first\n"
        "        b: second\n"
        '    """\n'
        "    return a + b\n"
        "\n"
        "\n"
        "def bad(a, b, c):\n"
        '    """Do it.\n'
        "\n"
        "    Args:\n"
        "        a: first\n"
        "        b: second\n"
        '    """\n'
        "    return a + b + c\n"
    )
    f = tmp_path / "d.py"
    f.write_text(code)
    res = darglint_skill.run("check_docstring_params", path=str(f))
    assert res["n_findings"] == 1
    finding = res["findings"][0]
    assert finding["function"] == "bad"
    assert finding["code"] == "DAR101"
    assert "'c'" in finding["message"]
    rep = darglint_skill.run("report", path=str(f))
    assert rep["per_file"] == {str(f): 1}


# -------------------------------------------------------------- interrogate


def test_interrogate_coverage_and_badge(tmp_path):
    code = (
        '"""Module."""\n'
        "\n"
        "\n"
        "class A:\n"
        '    """A."""\n'
        "\n"
        "    def method(self):\n"
        "        return 1\n"
        "\n"
        "\n"
        "def f():\n"
        '    """F."""\n'
    )
    f = tmp_path / "cov.py"
    f.write_text(code)
    res = interrogate_skill.run("coverage", path=str(f))
    # objects: module, class, method, function => 3/4 documented
    assert res["n_total"] == 4
    assert res["n_documented"] == 3
    assert res["overall_percent"] == 75.0
    badge = interrogate_skill.run("badge_level", percent=res["overall_percent"])
    assert badge["badge_color"] == "green"
    badge_low = interrogate_skill.run("badge_level", percent=20.0)
    assert badge_low["badge_color"] == "red"


# ------------------------------------------------------------------- pytest


@pytest.mark.skipif(shutil.which("pytest") is None and not has_module("pytest"),
                    reason="pytest missing")
def test_pytest_collection_and_run(tmp_path):
    (tmp_path / "test_t.py").write_text(
        "def test_ok():\n    assert 1 == 1\n\n"
        "def test_also_ok():\n    assert True\n"
    )
    coll = pytest_skill.run("run_collection_only", path=str(tmp_path))
    assert coll["n_collected"] == 2
    res = pytest_skill.run("run_short", path=str(tmp_path))
    assert res["passed"] == 2
    assert res["failed"] == 0
    rep = pytest_skill.run("report", path=str(tmp_path))
    assert rep["pass_rate_percent"] == 100.0


@pytest.mark.skipif(shutil.which("pytest") is None and not has_module("pytest"),
                    reason="pytest missing")
def test_pytest_run_short_failure(tmp_path):
    (tmp_path / "test_f.py").write_text("def test_bad():\n    assert 1 == 2\n")
    res = pytest_skill.run("run_short", path=str(tmp_path))
    assert res["failed"] >= 1
    assert res["returncode"] != 0


# ----------------------------------------------------------------- coverage


def test_coverage_parse_xml(tmp_path):
    xml = (
        '<?xml version="1.0" ?>\n'
        '<coverage version="6.5" line-rate="0.75" branch-rate="0.5">\n'
        "  <packages><package name=\"p\"><classes>\n"
        '    <class filename="a.py" line-rate="0.75">\n'
        "      <lines>\n"
        '        <line number="1" hits="1"/>\n'
        '        <line number="2" hits="1"/>\n'
        '        <line number="3" hits="1"/>\n'
        '        <line number="4" hits="0"/>\n'
        "      </lines>\n"
        "    </class>\n"
        "  </classes></package></packages>\n"
        "</coverage>\n"
    )
    f = tmp_path / "coverage.xml"
    f.write_text(xml)
    res = coverage_skill.run("parse_coverage_xml", path=str(f))
    assert res["line_coverage_percent"] == 75.0
    assert res["branch_rate"] == 0.5
    cls = res["files"][0]
    assert cls["covered"] == 3 and cls["valid"] == 4
    pct = coverage_skill.run("line_coverage_percent", path=str(f))
    assert pct["line_coverage_percent"] == 75.0


def test_coverage_run_requires_pytest_cov(tmp_path):
    if has_module("pytest_cov"):
        pytest.skip("pytest-cov installed")
    with pytest.raises(RuntimeError, match="pytest-cov"):
        coverage_skill.run("run", path=str(tmp_path))


# ------------------------------------------------------------------- mutmut


def test_mutmut_parse_junit_and_survival(tmp_path):
    junit = (
        '<?xml version="1.0" ?>\n'
        '<testsuite name="mutmut" tests="10" failures="3" errors="1" skipped="0">\n'
        "</testsuite>\n"
    )
    f = tmp_path / "junit.xml"
    f.write_text(junit)
    res = mutmut_skill.run("parse_results", path=str(f))
    assert res["engine"] == "junit-xml"
    assert res["counts"]["survived"] == 4
    assert res["counts"]["killed"] == 6
    surv = mutmut_skill.run("survival_rate", path=str(f))
    assert surv["survival_rate_percent"] == 40.0


def test_mutmut_parse_text(tmp_path):
    f = tmp_path / "results.txt"
    f.write_text("killed: 8\nsurvived: 2\ntimeout: 0\n")
    res = mutmut_skill.run("parse_results", path=str(f))
    assert res["counts"]["killed"] == 8
    assert res["total_mutants"] == 10


def test_mutmut_missing_binary(tmp_path):
    if shutil.which("mutmut"):
        pytest.skip("mutmut installed")
    with pytest.raises(RuntimeError, match="pip install mutmut"):
        mutmut_skill.run("run", path=str(tmp_path))


# ------------------------------------------------------------------- pydeps


def test_pydeps_graph_cycles_dot(two_module_pkg):
    res = pydeps_skill.run("import_graph", path=str(two_module_pkg))
    graph = res["graph"]
    assert set(graph) == {"a", "b", "c"}
    assert graph["a"] == ["b"]
    assert graph["b"] == ["a"]
    assert graph["c"] == []
    cyc = pydeps_skill.run("find_cycles", path=str(two_module_pkg))
    assert cyc["n_cycles"] == 1
    assert set(cyc["cycles"][0]) == {"a", "b"}
    dot = pydeps_skill.run("to_dot", path=str(two_module_pkg))
    assert dot["dot"].startswith("digraph")
    assert '"a" -> "b"' in dot["dot"]


# ----------------------------------------------------------------- sqlfluff


def test_sqlfluff_fallback(tmp_path):
    sql = (
        "SELECT * FROM users;\n"
        "DELETE FROM logs;\n"
        "UPDATE accounts SET balance = 0 WHERE id = 1;\n"
        "SELECT id FROM users WHERE id = 2;\n"
    )
    f = tmp_path / "q.sql"
    f.write_text(sql)
    res = sqlfluff_skill.run("lint", path=str(f))
    assert res["engine"] == "regex-fallback"
    assert res["n_violations"] == 2
    rules = sorted(v["rule"] for v in res["violations"])
    assert rules == ["L043", "L999"]
    assert {v["line"] for v in res["violations"]} == {1, 2}
    fix = sqlfluff_skill.run("fix_stub", path=str(f))
    assert len(fix["manual_fixes"]) == 2


def test_sqlfluff_no_violations(tmp_path):
    f = tmp_path / "ok.sql"
    f.write_text("SELECT id FROM t WHERE x = 1;\nDELETE FROM t WHERE x = 1;\n")
    res = sqlfluff_skill.run("lint", path=str(f))
    assert res["n_violations"] == 0


# ----------------------------------------------------------------- pgbadger


def test_pgbadger_parse_slow_queries():
    log = (
        "2024-05-01 12:00:01 UTC LOG:  duration: 1523.422 ms  statement: "
        "SELECT * FROM big_table WHERE x = 1;\n"
        "2024-05-01 12:00:05 UTC LOG:  duration: 12.003 ms  statement: "
        "SELECT 1;\n"
        "2024-05-01 12:00:09 UTC LOG:  duration: 845.000 ms  execute <unnamed>: "
        "UPDATE t SET a = 2;\n"
    )
    res = pgbadger_skill.run("parse_log_slow_queries", content=log,
                             min_duration_ms=100.0)
    assert res["n_queries"] == 2
    assert res["slowest_ms"] == pytest.approx(1523.422)
    assert res["queries"][0]["query"].startswith("SELECT * FROM big_table")
    assert "UPDATE t" in res["queries"][1]["query"]


def test_pgbadger_missing_binary():
    if shutil.which("pgbadger"):
        pytest.skip("pgbadger installed")
    with pytest.raises(RuntimeError, match="pgbadger"):
        pgbadger_skill.run("analyze", log_path="/nonexistent.log")


# ------------------------------------------------------ openapi validator


def test_openapi_validator_valid_spec():
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "Demo", "version": "1.0"},
        "paths": {"/items": {"get": {"responses": {"200": {"description": "ok"}}}}},
    }
    res = openapi_validator.run("validate", spec=spec)
    assert res["valid"]
    assert res["n_errors"] == 0


def test_openapi_validator_catches_missing_responses():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Broken"},
        "paths": {
            "/a": {"get": {"summary": "no responses"}},
            "/b": {},
        },
    }
    res = openapi_validator.run("validate", spec=spec)
    assert not res["valid"]
    locations = {e["location"] for e in res["errors"]}
    assert "$.paths./a.get.responses" in locations
    assert "$.paths./b" in locations


def test_openapi_validator_yaml_and_missing_version():
    res = openapi_validator.run("validate", content="info:\n  title: T\npaths: {}\n")
    assert not res["valid"]
    messages = " ".join(e["message"] for e in res["errors"])
    assert "openapi" in messages
    assert "non-empty" in messages


# ----------------------------------------------------------------- spectral


def test_spectral_fallback(tmp_path):
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "T"},
        "paths": {
            "/UserProfiles/{userId}": {
                "get": {
                    "parameters": [{"name": "userId", "in": "path"}],
                    "responses": {"200": {"description": "ok"}},
                },
                "post": {
                    "summary": "Create",
                    "operationId": "createProfile",
                    "parameters": [],
                    "responses": {"201": {"description": "made"}},
                },
            },
        },
    }
    res = spectral_skill.run("lint", spec=spec)
    assert res["engine"] == "fallback"
    rules = [f["rule"] for f in res["findings"]]
    # only the non-kebab UserProfiles segment violates; {userId} param is fine
    assert rules.count("path-kebab-case") == 1
    assert "operation-description" in rules  # get lacks summary/description
    assert "operation-operationId" in rules  # get lacks operationId
    assert "parameter-description" in rules  # userId param lacks description
    rep = spectral_skill.run("report", spec=spec)
    assert rep["by_severity"]["warn"] >= 3


# --------------------------------------------------------------- licenses


def test_license_classifier_buckets():
    lic = {
        "requests": "Apache-2.0",
        "attrs": "MIT",
        "qt-binding": "GPL-3.0",
        "mpl-lib": "LGPL-2.1",
        "internal-tool": "Proprietary",
        "mystery": "",
    }
    res = license_check.run("classify", licenses=lic)
    buckets = res["buckets"]
    assert set(buckets["permissive"]) == {"requests", "attrs"}
    assert buckets["proprietary"] == ["internal-tool"]
    assert buckets["unknown"] == ["mystery"]
    assert set(buckets["copyleft"]) == {"qt-binding", "mpl-lib"}
    flagged = license_check.run("flag_copyleft", licenses=lic)
    assert {f["package"] for f in flagged["flagged"]} == {"qt-binding", "mpl-lib"}
    summ = license_check.run("sbom_summary", licenses=lic)
    assert summ["counts"] == {"permissive": 2, "copyleft": 2,
                              "proprietary": 1, "unknown": 1}


# --------------------------------------------------------------- pipdeptree


def test_pipdeptree_tree_and_reverse():
    res = pipdeptree_skill.run("tree", packages=["pytest"])
    assert "pytest" in res["tree"]
    deps = res["tree"]["pytest"]
    assert "pluggy" in deps or "iniconfig" in deps
    rev = pipdeptree_skill.run("reverse_deps", package="pluggy")
    assert "pytest" in rev["reverse_dependencies"]


# -------------------------------------------------------------------- axe


def test_axe_analyze_html(tmp_path):
    html = (
        "<html>\n"
        "<head><title>t</title></head>\n"
        "<body>\n"
        '<img src="a.png">\n'
        "<form>\n"
        '  <input type="text" id="name">\n'
        "  <label for=\"name\">Name</label>\n"
        '  <input type="email">\n'
        "</form>\n"
        '<p style="font-size: 9px">tiny</p>\n'
        "</body>\n"
        "</html>\n"
    )
    f = tmp_path / "page.html"
    f.write_text(html)
    res = axe_skill.run("analyze_html", path=str(f))
    rules = [v["rule"] for v in res["violations"]]
    assert "html-has-lang" in rules
    assert rules.count("image-alt") == 1
    assert "page-has-heading-one" in rules
    # labelled input is fine; the unlabelled email input is flagged
    assert rules.count("label") == 1
    assert "small-font-inline-style" in rules
    rep = axe_skill.run("violations_report", path=str(f))
    assert rep["by_impact"]["critical"] == 2


def test_axe_clean_html():
    html = (
        '<html lang="en"><body><h1>Hi</h1>'
        '<img src="a.png" alt="a">'
        '<label for="n">Name</label><input type="text" id="n">'
        "</body></html>"
    )
    res = axe_skill.run("analyze_html", content=html)
    assert res["n_violations"] == 0


# ------------------------------------------------------------------- pa11y


def test_pa11y_summary_from_issues():
    issues = [
        {"type": "error", "code": "WCAG2AA.Principle1.1.1"},
        {"type": "error", "code": "WCAG2AA.Principle1.3.1"},
        {"type": "warning", "code": "WCAG2AA.Principle1.4.3"},
    ]
    res = pa11y_skill.run("issues_summary", issues=issues)
    assert res["by_type"] == {"error": 2, "warning": 1}
    assert res["by_code"]["WCAG2AA.Principle1.1.1"] == 1


def test_pa11y_missing_binary():
    if shutil.which("pa11y"):
        pytest.skip("pa11y installed")
    with pytest.raises(RuntimeError, match="pa11y"):
        pa11y_skill.run("run", url="http://example.com")


# ---------------------------------------------------------------- hadolint


def test_hadolint_fallback_catches_known_issues(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    dockerfile = (
        "FROM ubuntu:latest\n"
        "RUN apt-get update && apt-get install -y curl\n"
        "ADD app.py /srv/app.py\n"
        "RUN curl https://example.com/install.sh | sh\n"
        "ENTRYPOINT [\"python\", \"/srv/app.py\"]\n"
    )
    f = tmp_path / "Dockerfile"
    f.write_text(dockerfile)
    res = hadolint_skill.run("lint", path=str(f))
    rules = [i["rule"] for i in res["issues"]]
    assert "DL3007" in rules  # latest tag
    assert "DL3002" in rules  # missing USER
    assert "DL3009" in rules  # apt without rm lists
    assert "DL3020" in rules  # ADD instead of COPY
    assert "DL4001" in rules  # curl | sh
    score = hadolint_skill.run("score", path=str(f))
    assert score["score"] < 60


def test_hadolint_clean_dockerfile(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    dockerfile = (
        "FROM python:3.13-slim\n"
        "RUN apt-get update && apt-get install -y --no-install-recommends gcc \\\n"
        "    && rm -rf /var/lib/apt/lists/*\n"
        "COPY app.py /srv/app.py\n"
        "USER app\n"
        'ENTRYPOINT ["python", "/srv/app.py"]\n'
    )
    f = tmp_path / "Dockerfile"
    f.write_text(dockerfile)
    res = hadolint_skill.run("lint", path=str(f))
    assert res["n_issues"] == 0
    score = hadolint_skill.run("score", path=str(f))
    assert score["score"] == 100


# -------------------------------------------------------------------- trivy


def test_trivy_parse_json(tmp_path):
    report = {
        "SchemaVersion": 2,
        "Results": [
            {"Target": "requirements.txt", "Class": "lang-pkgs",
             "Vulnerabilities": [
                 {"VulnerabilityID": "CVE-2023-30861", "PkgName": "flask",
                  "Severity": "HIGH", "FixedVersion": "2.3.2"},
                 {"VulnerabilityID": "CVE-2023-25577", "PkgName": "werkzeug",
                  "Severity": "HIGH", "FixedVersion": "2.2.3"},
             ]},
            {"Target": "alpine:3.18 (alpine 3.18.0)", "Class": "os-pkgs",
             "Vulnerabilities": [
                 {"VulnerabilityID": "CVE-2023-0464", "PkgName": "openssl",
                  "Severity": "CRITICAL", "FixedVersion": "3.0.8-r0"},
                 {"VulnerabilityID": "CVE-2023-0465", "PkgName": "openssl",
                  "Severity": "LOW", "FixedVersion": ""},
             ]},
        ],
    }
    f = tmp_path / "trivy.json"
    f.write_text(json.dumps(report))
    res = trivy_skill.run("parse_json", path=str(f))
    assert res["n_vulnerabilities"] == 4
    assert res["by_severity"]["HIGH"] == 2
    assert res["by_severity"]["CRITICAL"] == 1
    assert res["by_severity"]["LOW"] == 1
    assert res["by_severity"]["MEDIUM"] == 0


def test_trivy_missing_binary():
    if shutil.which("trivy"):
        pytest.skip("trivy installed")
    with pytest.raises(RuntimeError, match="trivy"):
        trivy_skill.run("scan", target=".")


# ------------------------------------------------------------------ checkov


def test_checkov_parse_results(tmp_path):
    report = {
        "check_type": "terraform",
        "summary": {"passed": 5, "failed": 2, "skipped": 1,
                    "parsing_errors": 0, "resource_count": 10},
        "results": {
            "failed_checks": [
                {"check_id": "CKV_AWS_20", "check_name": "S3 bucket ...",
                 "file_path": "/main.tf", "file_line_range": [12, 20],
                 "resource": "aws_s3_bucket.data"},
                {"check_id": "CKV_AWS_21", "check_name": "S3 versioning",
                 "file_path": "/main.tf", "file_line_range": [12, 20],
                 "resource": "aws_s3_bucket.data"},
            ],
            "passed_checks": [{"check_id": "CKV_AWS_1"}] * 5,
        },
    }
    f = tmp_path / "checkov.json"
    f.write_text(json.dumps(report))
    res = checkov_skill.run("parse_results", path=str(f))
    assert res["passed"] == 5
    assert res["failed"] == 2
    assert res["skipped"] == 1
    assert res["failed_checks"][0]["check_id"] == "CKV_AWS_20"
    assert res["failed_checks"][0]["line"] == 12


def test_checkov_missing_binary(tmp_path):
    if shutil.which("checkov"):
        pytest.skip("checkov installed")
    with pytest.raises(RuntimeError, match="pip install checkov"):
        checkov_skill.run("scan", path=str(tmp_path))


# ----------------------------------------------------------- import linter


def test_import_linter_layers(tmp_path):
    (tmp_path / "db.py").write_text("import services\n")
    (tmp_path / "services.py").write_text("import db\n")
    (tmp_path / "api.py").write_text("import services\nimport db\n")
    layers = ["db", "services", "api"]
    res = import_linter_skill.run(
        "check_contracts", path=str(tmp_path), layers=layers)
    assert not res["kept"]
    assert res["n_violations"] == 1  # db -> services (higher layer)
    bad = {(v["module"], v["imports"]) for v in res["violations"]}
    assert ("db", "services") in bad
    assert ("api", "services") not in bad  # allowed: api is highest
    vio = import_linter_skill.run("violations", path=str(tmp_path), layers=layers)
    assert "db" in vio["by_module"]


def test_import_linter_clean(tmp_path):
    (tmp_path / "db.py").write_text("X = 1\n")
    (tmp_path / "services.py").write_text("import db\n")
    (tmp_path / "api.py").write_text("import services\n")
    res = import_linter_skill.run(
        "check_contracts", path=str(tmp_path), layers=["db", "services", "api"])
    assert res["kept"]
    assert res["n_violations"] == 0


# -------------------------------------------------------- architecture rules


def test_arch_rules_layer_and_fanout(tmp_path):
    (tmp_path / "ui.py").write_text("import db\nimport helpers\n")
    (tmp_path / "db.py").write_text("import helpers\n")
    (tmp_path / "helpers.py").write_text("VALUE = 1\n")
    rules = [{"module": "db", "forbidden": ["ui"]}]
    res = arch_rules.run("check_layer_rule", path=str(tmp_path), rules=rules)
    assert res["passed"]
    rules = [{"module": "ui", "forbidden": ["db"]}]
    res = arch_rules.run("check_layer_rule", path=str(tmp_path), rules=rules)
    assert not res["passed"]
    assert res["violations"][0]["module"] == "ui"
    assert res["violations"][0]["imports"] == "db"
    fan = arch_rules.run("module_fan_out_report", path=str(tmp_path))
    assert fan["modules"][0]["module"] == "ui"
    assert fan["modules"][0]["fan_out"] == 2


def test_arch_rules_cyclic_packages(tmp_path):
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("import a\n")
    res = arch_rules.run("cyclic_packages", path=str(tmp_path))
    assert res["n_cycles"] == 1
    assert set(res["packages_in_cycles"]) == {"a", "b"}
    clean = arch_rules.run("cyclic_packages", graph={"a": {"b"}, "b": set()})
    assert clean["n_cycles"] == 0


# ------------------------------------------------------------ risk analysis


def test_risk_scoring_and_mitigation():
    risks = [
        {"name": "data loss", "likelihood": 2, "impact": 5},
        {"name": "delay", "likelihood": 4, "impact": 3},
        {"name": "typo", "likelihood": 1, "impact": 1},
    ]
    res = risk_analysis.run("score_risks", risks=risks)
    scores = {r["name"]: r["score"] for r in res["risks"]}
    assert scores == {"data loss": 10.0, "delay": 12.0, "typo": 1.0}
    assert res["risks"][0]["name"] == "delay"  # sorted desc
    top = risk_analysis.run("top_risks", risks=risks, n=1)
    assert top["top"][0]["name"] == "delay"
    req = risk_analysis.run("mitigation_required", risks=risks, threshold=9)
    assert {r["name"] for r in req["risks"]} == {"data loss", "delay"}


# -------------------------------------------------------------- mitigation


def test_mitigation_plan_and_template():
    risks = [
        {"name": "big", "likelihood": 5, "impact": 4},
        {"name": "mid", "likelihood": 3, "impact": 3},
        {"name": "small", "likelihood": 1, "impact": 2},
    ]
    res = mitigation.run("plan", risks=risks)
    strat = {p["name"]: p["strategy"] for p in res["plan"]}
    assert strat["big"] == "avoid"
    assert strat["mid"] == "mitigate"
    assert strat["small"] == "accept"
    custom = mitigation.run("plan", risks=risks, strategies={"big": "mitigate"})
    assert {p["name"]: p["strategy"] for p in custom["plan"]}["big"] == "mitigate"
    md = mitigation.run("template", project="Demo", risks=risks)
    assert "| R1 |" in md["template"] or "avoid" in md["template"]
    with pytest.raises(ValueError, match="strategy"):
        mitigation.run("plan", risks=risks, strategies={"big": "flee"})


# -------------------------------------------------------- resource planning


def test_fte_and_conflicts_and_gantt():
    tasks = [
        {"name": "design", "hours": 80, "role": "dev"},
        {"name": "build", "hours": 160, "role": "dev"},
        {"name": "write docs", "hours": 20, "role": "writer"},
    ]
    res = resource_planning.run("fte_estimate", tasks=tasks)
    assert res["total_hours"] == 260.0
    assert res["fte_weeks"] == 6.5
    assert res["by_role"]["dev"]["fte_weeks"] == 6.0

    allocs = [
        {"resource": "ana", "task": "t1", "start": 1, "end": 5},
        {"resource": "ana", "task": "t2", "start": 4, "end": 8},
        {"resource": "bob", "task": "t3", "start": 1, "end": 3},
    ]
    conf = resource_planning.run("timeline_conflict", allocations=allocs)
    assert conf["has_conflicts"]
    assert conf["n_conflicts"] == 1
    assert conf["conflicts"][0]["overlap_start"] == 4
    assert conf["conflicts"][0]["overlap_end"] == 5

    gantt = resource_planning.run("gantt_data", tasks=[
        {"name": "A", "start": 0, "end": 3},
        {"name": "B", "start": 3, "end": 7, "resource": "ana"},
    ])
    assert gantt["span"] == {"start": 0, "end": 7}
    assert gantt["bars"][1]["duration"] == 4


# ------------------------------------------------------------------ timeline


def test_cpm_matches_hand_calc():
    tasks = [
        {"name": "A", "duration": 3},
        {"name": "B", "duration": 2, "deps": ["A"]},
        {"name": "C", "duration": 4, "deps": ["A"]},
        {"name": "D", "duration": 1, "deps": ["B", "C"]},
    ]
    # hand calc: A(0-3), B(3-5), C(3-7), D(7-8); critical: A-C-D => 8
    cp = timeline.run("critical_path", tasks=tasks)
    assert cp["duration"] == 8.0
    assert cp["critical_path"] == ["A", "C", "D"]
    sched = timeline.run("earliest_schedule", tasks=tasks)
    es = {s["name"]: (s["earliest_start"], s["earliest_finish"]) for s in sched["schedule"]}
    assert es == {"A": (0.0, 3.0), "B": (3.0, 5.0),
                  "C": (3.0, 7.0), "D": (7.0, 8.0)}
    slack = timeline.run("slack", tasks=tasks)
    assert slack["slack"] == {"A": 0.0, "B": 2.0, "C": 0.0, "D": 0.0}


def test_cpm_cycle_detected():
    tasks = [
        {"name": "A", "duration": 1, "deps": ["B"]},
        {"name": "B", "duration": 1, "deps": ["A"]},
    ]
    with pytest.raises(ValueError, match="cycle"):
        timeline.run("critical_path", tasks=tasks)


# ------------------------------------------------------------------- cost


def test_cost_estimate_breakdown_contingency():
    resources = [
        {"name": "dev", "hours": 40, "rate": 100, "category": "labor"},
        {"name": "cloud", "hours": 10, "rate": 50, "category": "infra"},
    ]
    est = cost_model.run("estimate", resources=resources)
    assert est["total_cost"] == 4500.0
    br = cost_model.run("breakdown_by_category", resources=resources)
    assert br["by_category"]["labor"]["cost"] == 4000.0
    assert br["by_category"]["infra"]["cost"] == 500.0
    assert br["by_category"]["infra"]["share_percent"] == pytest.approx(11.11)
    con = cost_model.run("contingency", resources=resources, percent=10)
    assert con["contingency"] == 450.0
    assert con["total_with_contingency"] == 4950.0
    con2 = cost_model.run("contingency", total=1000, percent=15)
    assert con2["contingency"] == 150.0


# ----------------------------------------------------------------- budget


def test_budget_allocate_variants():
    reqs = [
        {"name": "A", "requested": 100, "priority": 2},
        {"name": "B", "requested": 100, "priority": 1},
        {"name": "C", "requested": 100, "priority": 3},
    ]
    prop = budget_opt.run("allocate", requests=reqs, cap=150)
    assert prop["strategy"] == "proportional"
    assert all(a["allocated"] == 50.0 for a in prop["allocations"])
    assert prop["total_allocated"] == 150.0
    greedy = budget_opt.run("allocate", requests=reqs, cap=150, strategy="greedy")
    by_name = {a["name"]: a["allocated"] for a in greedy["allocations"]}
    assert by_name == {"B": 100.0, "A": 50.0, "C": 0.0}


def test_budget_variance():
    rep = budget_opt.run("variance_report",
                         planned={"A": 100, "B": 200},
                         actual={"A": 120, "B": 180})
    assert rep["total_variance"] == 0
    rows = {r["name"]: r for r in rep["items"]}
    assert rows["A"]["variance"] == 20.0
    assert rows["A"]["variance_percent"] == 20.0
    assert rows["B"]["variance"] == -20.0


def test_budget_year_plan_burn_forecast():
    plan = budget_plan.run("year_plan", total_budget=100000,
                           weights=[2, 1, 1, 2])
    assert sum(plan["quarters"].values()) == pytest.approx(100000.0)
    assert plan["quarters"]["Q1"] == pytest.approx(100000 / 3)
    burn = budget_plan.run("burn_rate", spent=20000, elapsed_weeks=10)
    assert burn["burn_rate_per_week"] == 2000.0
    fc = budget_plan.run("forecast_eoy", total_budget=100000, spent=20000,
                         elapsed_weeks=10)
    assert fc["forecast_eoy_spend"] == pytest.approx(104000.0)
    assert not fc["on_track"]
    fc_ok = budget_plan.run("forecast_eoy", total_budget=100000, spent=10000,
                            elapsed_weeks=25)
    assert fc_ok["on_track"]
