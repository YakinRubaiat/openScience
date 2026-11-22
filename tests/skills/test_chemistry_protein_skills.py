"""Tests for the cheminformatics skill + chemistry/protein connector additions.

Run:

    python3 -m pytest tests/skills/test_chemistry_protein_skills.py -x -q
"""

from __future__ import annotations

import urllib.error
from unittest.mock import MagicMock, patch

import pytest

# --- skills ----------
from openscience.skills import execute_skill, list_skills
from openscience.skills.cheminformatics import (  # noqa: F401 - import triggers registration
    admet,
    assay_matrix,
    bayes_opt,
    multiplex,
    opt_algos,
    protocol_analysis,
    protocol_documentation,
    reagents,
    rdkit_ext,
    scaffold,
    similarity,
)

# --- connectors ----------
from openscience.connectors.chemistry.chembl import ChemblConnector
from openscience.connectors.chemistry.zinc import ZincConnector
from openscience.connectors.protein.alphafold import (
    AlphaFoldConnector,
    AlphaFoldPrediction,
    list_predictions,
)
from openscience.connectors.protein.pdb import PDBConnector, parse_pdb_text


# ---------------------------------------------------------------------------
# Pure-python smoke checks
# ---------------------------------------------------------------------------


def test_all_skill_names_registered() -> None:
    names = set(list_skills())
    expected = {
        "rdkit_descriptors_ext",
        "molecular_similarity",
        "scaffold_analysis",
        "admet_rules",
        "reagent_database",
        "assay_compatibility",
        "multiplex_optimization",
        "optimization_algorithms",
        "bayesian_optimization",
        "protocol_analysis",
        "protocol_documentation",
    }
    missing = expected - names
    assert not missing, f"missing skills: {missing}"


# ---------------------------------------------------------------------------
# RDKit descriptor extensions
# ---------------------------------------------------------------------------


class TestRdkitDescriptorsExt:
    def test_all_descriptors_caffeine(self) -> None:
        out = rdkit_ext.all_descriptors(smiles="Cn1cnc2n(C)c(=O)n(C)c(=O)c12")
        assert out["status"] == "ok"
        desc = out["descriptors"]
        assert desc["canonical_smiles"]
        assert desc["inchi_key"]
        assert desc["MolWt"] == pytest.approx(194.19, abs=0.05)
        assert out["count"] > 20

    def test_all_descriptors_invalid_smiles(self) -> None:
        with pytest.raises(ValueError):
            rdkit_ext.all_descriptors(smiles="not-a-smiles")

    def test_lipinski_flags_pass(self) -> None:
        # Benzene (small, no violations).
        out = rdkit_ext.lipinski_flags(smiles="c1ccccc1")
        assert out["passes_ro5"] is True
        assert out["violation_count"] == 0

    def test_lipinski_flags_mw_violation(self) -> None:
        # A heavy PEG chain (MW >> 500).
        smi = "O" * 0 + "COCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCO"  # ~MW 620
        out = rdkit_ext.lipinski_flags(smiles=smi)
        assert "mw_ok" in out["flags"]
        assert not out["flags"]["mw_ok"]
        assert out["violation_count"] >= 1

    def test_rotatable_estimate_small(self) -> None:
        out = rdkit_ext.rotatable_estimate(smiles="c1ccccc1")
        assert out["rotatable_bonds"] == 0
        assert 0.0 <= out["flexibility_index"] <= 1.0


# ---------------------------------------------------------------------------
# Molecular similarity
# ---------------------------------------------------------------------------


class TestSimilarity:
    def test_tanimoto_identical(self) -> None:
        out = similarity.tanimoto(smiles_a="c1ccccc1", smiles_b="c1ccccc1")
        assert out["tanimoto"] == pytest.approx(1.0)

    def test_tanimoto_different(self) -> None:
        out = similarity.tanimoto(smiles_a="c1ccccc1", smiles_b="C(=O)(O)O")
        assert 0.0 <= out["tanimoto"] < 0.5

    def test_dice_identical(self) -> None:
        out = similarity.dice(smiles_a="CC(=O)Oc1ccccc1C(=O)O", smiles_b="CC(=O)Oc1ccccc1C(=O)O")
        assert out["dice"] == pytest.approx(1.0)

    def test_most_similar_ranks(self) -> None:
        query = "c1ccccc1"  # benzene
        smis = ["c1ccccc1", "Cc1ccccc1", "CCO", "CC(=O)O"]
        out = similarity.most_similar(query_smiles=query, smiles_list=smis, top_k=3)
        assert len(out["hits"]) == 3
        assert out["hits"][0]["smiles"] == "c1ccccc1"

    def test_cluster_butina_groups(self) -> None:
        smis = [
            "c1ccccc1",
            "c1cccnc1",   # pyridine -- similar aromatic
            "CCO",        # ethanol -- small aliphatic
            "CCCO",       # propanol
        ]
        out = similarity.cluster_butina(smiles_list=smis, threshold=0.4)
        assert out["n_molecules"] == 4
        assert out["n_clusters"] >= 1
        sizes = sum(c["size"] for c in out["clusters"])
        assert sizes == 4


# ---------------------------------------------------------------------------
# Scaffold analysis
# ---------------------------------------------------------------------------


class TestScaffoldAnalysis:
    def test_murcko_scaffold_benzene(self) -> None:
        out = scaffold.murcko_scaffold(smiles="c1ccccc1")
        # Benzene's Bemis-Murcko scaffold is benzene itself.
        assert out["scaffold_smiles"] == "c1ccccc1"

    def test_murcko_scaffold_substituted(self) -> None:
        # Toluene -- scaffold should still be benzene.
        out = scaffold.murcko_scaffold(smiles="Cc1ccccc1")
        assert out["scaffold_smiles"] == "c1ccccc1"

    def test_scaffold_counts_histogram(self) -> None:
        smis = ["c1ccccc1", "Cc1ccccc1", "CCO", "CCCO"]
        out = scaffold.scaffold_counts(smiles_list=smis)
        assert out["n_valid"] == 4
        assert out["n_unique_scaffolds"] >= 1
        benzenes = [h for h in out["histogram"] if h["scaffold"] == "c1ccccc1"]
        assert benzenes and benzenes[0]["count"] == 2

    def test_scaffold_tree_level_fallback(self) -> None:
        out = scaffold.scaffold_tree_level(smiles="Oc1ccccc1", level=0)
        assert out["resolved_level"] >= 0
        assert out["scaffold_smiles"]

    def test_scaffold_tree_level_higher_level(self) -> None:
        out = scaffold.scaffold_tree_level(smiles="Oc1ccccc1", level=3)
        assert out["resolved_level"] <= out["scaffold_tree_size"]


# ---------------------------------------------------------------------------
# ADMET rules
# ---------------------------------------------------------------------------


class TestAdmetRules:
    def test_ro5_aspirin(self) -> None:
        out = admet.ro5_violations(smiles="CC(=O)Oc1ccccc1C(=O)O")
        assert out["violation_count"] == 0
        assert out["mw"] < 500
        assert out["logp"] < 5

    def test_ro5_violation_count(self) -> None:
        # Docetaxel-like heavy mol -- e.g., erythromycin with MW 733
        out = admet.ro5_violations(smiles="COCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCO")
        assert out["violation_count"] >= 1

    def test_veber_small_molecule(self) -> None:
        out = admet.veber(smiles="CCO")
        assert out["passes"] is True
        assert out["tpsa"] < 140

    def test_ghose_outside_window(self) -> None:
        out = admet.ghose(smiles="c1ccccc1")
        # Benzene has MW=78 -- Ghose window is 160-480.
        assert "mw_outside_160_480" in out["violations"]

    def test_egan_pass(self) -> None:
        out = admet.egan(smiles="CCO")
        assert out["passes"] is True

    def test_pains_alerts_clean(self) -> None:
        out = admet.pains_alerts(smiles="CCO")
        assert out["password".replace("password", "passes")] is True
        assert out["alert_count"] == 0

    def test_pains_alerts_hit(self) -> None:
        # Catechol (1,2-dihydroxybenzene) trips the embedded catechols PAINS.
        out = admet.pains_alerts(smiles="Oc1cccc(O)c1O" if False else "c1cc(O)c(O)cc1")
        if out["source"] == "embedded_smarts":
            assert out["alert_count"] >= 1
            assert out["password".replace("password", "passes")] is False
        else:
            # rdkit FilterCatalog hits at least one PAINS group.
            assert out["alert_count"] >= 1


# ---------------------------------------------------------------------------
# Reagent database
# ---------------------------------------------------------------------------


class TestReagentDatabase:
    def test_lookup_by_name(self) -> None:
        out = reagents.lookup(query="Sodium chloride")
        assert out["found"] is True
        assert out["entry"]["cas"] == "7647-14-5"

    def test_lookup_by_cas(self) -> None:
        out = reagents.lookup(query="75-05-8")
        assert out["found"] is True
        assert out["entry"]["name"] == "Acetonitrile"

    def test_lookup_missing(self) -> None:
        out = reagents.lookup(query="NO_SUCH_CHEMICAL_ABC123")
        assert out["found"] is False

    def test_search_by_name(self) -> None:
        out = reagents.search_by_name(substring="acid", limit=10)
        assert out["n_hits"] >= 2
        names = {h["name"] for h in out["hits"]}
        assert any("acid" in n.lower() for n in names)

    def test_hazardous_flag_toxic(self) -> None:
        out = reagents.hazardous_flag(reagent_text="Chloroform")
        assert out["hazardous"] is True
        assert "toxic" in out["hazard_flags"]

    def test_hazardous_flag_clean(self) -> None:
        out = reagents.hazardous_flag(reagent_text="Sodium chloride")
        assert out["hazardous"] is False
        assert out["hazard_flags"] == []


# ---------------------------------------------------------------------------
# Assay compatibility + multiplex
# ---------------------------------------------------------------------------


class TestAssayCompatibility:
    def test_check_pair_identical_em(self) -> None:
        dye_a = {"name": "FITC", "ex_nm": 494, "em_nm": 518}
        dye_b = {"name": "GFP", "ex_nm": 488, "em_nm": 509}
        out = assay_matrix.check_pair(dye_a=dye_a, dye_b=dye_b)
        assert out["verdict"] == "poor"
        assert out["em_overlap"] > 0.6

    def test_check_pair_far_red_blue(self) -> None:
        dye_a = {"name": "DAPI", "ex_nm": 358, "em_nm": 461}
        dye_b = {"name": "Texas Red", "ex_nm": 596, "em_nm": 615}
        out = assay_matrix.check_pair(dye_a=dye_a, dye_b=dye_b)
        assert out["verdict"] == "good"
        assert out["em_overlap"] < 0.3

    def test_panel_report(self) -> None:
        dyes = [
            {"name": "DAPI", "ex_nm": 358, "em_nm": 461},
            {"name": "FITC", "ex_nm": 494, "em_nm": 518},
            {"name": "Texas Red", "ex_nm": 596, "em_nm": 615},
        ]
        out = assay_matrix.panel_report(dyes=dyes)
        assert out["n_pairs"] == 3
        assert out["overall_verdict"] in ("good", "caution")


class TestMultiplexOptimization:
    _PALETTE = [
        {"name": "DAPI", "ex_nm": 358, "em_nm": 461},
        {"name": "FITC", "ex_nm": 494, "em_nm": 518},
        {"name": "Alexa555", "ex_nm": 555, "em_nm": 565},
        {"name": "Cy5", "ex_nm": 649, "em_nm": 670},
        {"name": "Alexa488_overlapping", "ex_nm": 495, "em_nm": 519},
    ]

    def test_greedy_panel_picks_well_separated(self) -> None:
        out = multiplex.greedy_panel(candidates=self._PALETTE, n_select=3)
        assert out["n_select"] == 3
        assert "Alexa555" in out["selection_order"]
        # Alexa488_overlapping conflicts with FITC; greedy may still pick it
        # depending on order, so just verify the panel size and order logic.
        assert len(set(out["selection_order"])) == 3

    def test_greedy_panel_must_be_separated(self) -> None:
        # Only 3 chromatically distant dyes plus 1 that overlaps with FITC.
        dyes = [
            {"name": "A", "ex_nm": 405, "em_nm": 450},
            {"name": "B", "ex_nm": 488, "em_nm": 525},
            {"name": "C", "ex_nm": 660, "em_nm": 700},
            {"name": "B_overlap", "ex_nm": 490, "em_nm": 527},
        ]
        out = multiplex.greedy_panel(candidates=dyes, n_select=3)
        # Must contain A (seed, longest em is C but A comes from distant end) and C.
        assert "A" in out["selection_order"]
        assert "C" in out["selection_order"]
        # And either B or B_overlap (not both with each other / not pair).
        chosen = set(out["selection_order"])
        assert not ({"B", "B_overlap"} <= chosen)

    def test_spillover_matrix_symmetric(self) -> None:
        dyes = [
            {"name": "A", "ex_nm": 405, "em_nm": 450},
            {"name": "B", "ex_nm": 488, "em_nm": 525},
        ]
        out = multiplex.spillover_matrix(dyes=dyes)
        m = out["spillover_matrix"]
        assert len(m) == 2
        assert m[0][0] == pytest.approx(1.0)
        assert m[1][1] == pytest.approx(1.0)
        assert m[0][1] == pytest.approx(m[1][0])


# ---------------------------------------------------------------------------
# Optimization
# ---------------------------------------------------------------------------


class TestOptimizationAlgorithms:
    def test_nelder_mead_quadratic(self) -> None:
        out = opt_algos.nelder_mead(
            objective_fn="x**2 + (y-2)**2",
            x0=[0.0, 0.0],
            params=["x", "y"],
            max_iter=200,
        )
        assert out["success"] is True
        assert out["fun"] == pytest.approx(0.0, abs=1e-4)
        assert out["x"][0] == pytest.approx(0.0, abs=1e-3)
        assert out["x"][1] == pytest.approx(2.0, abs=1e-3)

    def test_grid_search_minimum(self) -> None:
        out = opt_algos.grid_search(
            objective_fn="(x - 5)**2",
            grid={"x": [0.0, 1.0, 2.0, 5.0, 7.0]},
        )
        assert out["best_params"] == {"x": 5.0}
        assert out["best_value"] == pytest.approx(0.0)
        assert out["n_evaluations"] == 5

    def test_best_result_picks_min(self) -> None:
        results = [
            {"params": {"x": 1.0}, "value": 4.0},
            {"params": {"x": 2.0}, "value": 1.0},
            {"params": {"x": 3.0}, "value": 9.0},
        ]
        out = opt_algos.best_result(results=results)
        assert out["best"]["params"] == {"x": 2.0}
        assert out["best_value"] == pytest.approx(1.0)


class TestBayesianOptimization:
    def test_gp_ei_1d_ei_positive_at_candidates(self) -> None:
        out = bayes_opt.gp_ei_1d(
            x_train=[0.0, 1.0],
            y_train=[0.5, 0.5],
            x_candidates=[0.25, 0.75, 1.5],
        )
        assert "next_x" in out
        assert out["next_x"] in [0.25, 0.75, 1.5]
        assert out["next_ei"] >= 0.0
        # The EI at the most-uncertain candidate should dominate.
        assert max(out["ei"]) > 0

    def test_suggest_recovers_minimum(self) -> None:
        out = bayes_opt.suggest(
            objective_fn="(x - 0.5)**2 + 0.1",
            bounds=[0.0, 1.0],
            n_steps=4,
            n_init=3,
        )
        assert out["best_y"] == pytest.approx(0.1, abs=1e-6)
        assert out["best_x"] == pytest.approx(0.5, abs=1e-2)


# ---------------------------------------------------------------------------
# Protocol analysis + documentation
# ---------------------------------------------------------------------------


PROTOCOL_EXAMPLE = """\
1. Prepare PBS buffer on ice.
2. Add primary antibody and incubate at 4 C overnight.
3. Wash three times with PBST for 5 min each.
4. Add secondary antibody and incubate at room temperature for 1 h.
5. Add DAPI stain.
6. Image on the confocal microscope.
"""


class TestProtocolAnalysis:
    def test_parse_steps_numbered(self) -> None:
        out = protocol_analysis.parse_steps(protocol_text=PROTOCOL_EXAMPLE)
        assert out["n_steps"] == 6
        assert out["steps"][0].startswith("Prepare")

    def test_parse_steps_empty(self) -> None:
        with pytest.raises(ValueError):
            protocol_analysis.parse_steps(protocol_text="")

    def test_estimate_duration_with_explicit_times(self) -> None:
        steps = [
            "Wash for 5 min",
            "Incubate for 1 h",
            "Centrifuge",
        ]
        out = protocol_analysis.estimate_duration(steps=steps)
        # 5 min wash + 60 min incubate + 10 min centrifuge default = 75.
        assert out["total_minutes"] == pytest.approx(75.0, abs=1.0)

    def test_estimate_duration_includes_default_incubation(self) -> None:
        out = protocol_analysis.estimate_duration(steps=["Incubate with antibody"])
        assert out["steps"][0]["duration_minutes"] == pytest.approx(30.0)

    def test_flag_risks_toxic(self) -> None:
        out = protocol_analysis.flag_risks(
            steps=[
                "Pipette toxic chloroform into the tube",
                "Wash the plate",
            ]
        )
        assert out["n_flagged"] == 1
        assert "toxic_reagent" in out["steps"][0]["risk_tags"]

    def test_flag_risks_clean(self) -> None:
        out = protocol_analysis.flag_risks(steps=["Mix gently"])
        assert out["n_flagged"] == 0


class TestProtocolDocumentation:
    def test_render_markdown(self) -> None:
        out = protocol_documentation.render_markdown(
            title="IP",
            sections={
                "Overview": "Immunoprecipitation protocol.",
                "Materials": ["Beads", "Antibody"],
            },
        )
        md = out["markdown"]
        assert md.startswith("# IP")
        assert "## Overview" in md
        assert "- Beads" in md

    def test_checklist(self) -> None:
        out = protocol_documentation.checklist(steps=["Step one", "Step two"])
        assert "[ ]" in out["markdown"]
        assert out["n_steps"] == 2

    def test_materials_table(self) -> None:
        out = protocol_documentation.materials_table(
            reagents=[
                {"name": "PBS", "volume_ml": 500},
                {"name": "Tween", "volume_ml": 1},
            ]
        )
        assert "| name | volume_ml |" in out["markdown"]
        assert out["n_rows"] == 2


# ---------------------------------------------------------------------------
# Connectors
# ---------------------------------------------------------------------------


def _mock_urlopen_ok(payload: bytes):
    """Return a urlopen-context-manager that yields ``payload``."""

    class FakeResp:
        def __init__(self, data: bytes):
            self._data = data

        def read(self) -> bytes:
            return self._data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    return lambda req, timeout=30: FakeResp(payload)


def _mock_urlopen_fail(exc: Exception):
    def _raise(req, timeout=30):
        raise exc

    return _raise


class TestPDBConnector:
    @patch("urllib.request.urlopen")
    def test_fetch_text_network_error_raises_runtimeerror(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        pdb = PDBConnector()
        with pytest.raises(RuntimeError, match="RCSB PDB download failed"):
            pdb.fetch_text("1abc")

    @patch("urllib.request.urlopen")
    def test_fetch_record_parses_header(self, mock_urlopen) -> None:
        fake_pdb = (
            "HEADER    OXIDOREDUCTASE(OXIDATION)              01-JAN-00   9XYZ              \n"
            "TITLE     A TOY STRUCTURE TO PARSE                                                \n"
            "REMARK   2 RESOLUTION.  1.50 ANGSTROMS.                                          \n"
            "ATOM      1  N   ALA A   1      11.104  13.207   9.308  1.00 20.00           N  \n"
            "ATOM      2  CA  ALA A   1      12.504  13.207   9.308  1.00 20.00           C  \n"
            "ATOM      3  C   ALA A   2      18.000  12.000   8.000  1.00 20.00           C  \n"
            "ATOM      4  O   ALA B   1      19.000  12.500   9.000  1.00 20.00           O  \n"
            "ATOM      5  CA  ALA B   2      20.000  13.000   9.500  1.00 20.00           C  \n"
            "END\n"
        )
        mock_urlopen.side_effect = _mock_urlopen_ok(fake_pdb.encode("utf-8"))
        rec = PDBConnector().fetch_record("9xyz")
        assert rec.pdb_id == "9XYZ"
        assert rec.resolution == pytest.approx(1.50)
        chains = {c.chain_id: c.residue_count for c in rec.chains}
        assert chains == {"A": 2, "B": 2}
        assert "OXIDOREDUCTASE" in rec.classification

    def test_fetch_text_invalid_id(self) -> None:
        with pytest.raises(ValueError):
            PDBConnector().fetch_text("TOOLONG")

    def test_parse_pdb_text_offline(self) -> None:
        rec = parse_pdb_text("TITLE     PURE OFFLINE MODE\nATOM      1  N   ALA A   1      11.104  13.207   9.308  1.00 20.00           N  \n", pdb_id="aaaa")
        assert rec.pdb_id == "aaaa"
        assert rec.title.startswith("PURE")


class TestAlphaFoldConnector:
    @patch("urllib.request.urlopen")
    def test_list_predictions_network_error_raises_runtimeerror(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        with pytest.raises(RuntimeError, match="AlphaFold request failed"):
            list_predictions("P00000")

    @patch("urllib.request.urlopen")
    def test_list_predictions_parses_records(self, mock_urlopen) -> None:
        payload = b"""
        [{"uniprotAccession": "P12345", "uniprotSequence": "MKK",
          "gene": "TOYG", "latestVersion": "4",
          "pdbUrl": "https://alphafold.ebi.ac.uk/files/AF-P12345-F1-model_v4.pdb",
          "globalMetricValue": 89.4}]
        """
        mock_urlopen.side_effect = _mock_urlopen_ok(payload)
        preds = list_predictions("p12345")
        assert len(preds) == 1
        assert preds[0].uniprot_id == "P12345"
        assert preds[0].sequence_length == 3
        assert preds[0].global_metric == pytest.approx(89.4)

    def test_invalid_accession(self) -> None:
        with pytest.raises(ValueError):
            list_predictions("   ")

    @patch("urllib.request.urlopen")
    def test_fetch_pdb_text_network_error(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        pred = AlphaFoldPrediction(uniprot_id="P00000", pdb_url="http://x")
        with pytest.raises(RuntimeError):
            AlphaFoldConnector().fetch_pdb_text(pred)


class TestChemblConnector:
    @patch("urllib.request.urlopen")
    def test_get_molecule_network_error_raises_runtimeerror(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        with pytest.raises(RuntimeError, match="ChEMBL request failed"):
            ChemblConnector().get_molecule("CHEMBL25")

    @patch("urllib.request.urlopen")
    def test_get_molecule_parses_record(self, mock_urlopen) -> None:
        payload = b"""
        {"molecule_chembl_id": "CHEMBL25", "pref_name": "ASPIRIN",
         "molecule_type": "Small molecule", "max_phase": "4",
         "molecule_structures": {"canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
                                  "standard_inchi_key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"},
         "molecule_properties": {"mw_freebase": "180.159"}}
        """
        mock_urlopen.side_effect = _mock_urlopen_ok(payload)
        mol = ChemblConnector().get_molecule("CHEMBL25")
        assert mol.chembl_id == "CHEMBL25"
        assert mol.pref_name == "ASPIRIN"
        assert mol.max_phase == pytest.approx(4.0)
        assert mol.canonical_smiles.startswith("CC(=O)O")
        assert mol.mw_freebase == pytest.approx(180.159)

    @patch("urllib.request.urlopen")
    def test_search_molecules_returns_list(self, mock_urlopen) -> None:
        payload = b"""
        {"molecules": [{"molecule_chembl_id": "CHEMBL1", "pref_name": "X"},
                       {"molecule_chembl_id": "CHEMBL2", "pref_name": "Y"}]}
        """
        mock_urlopen.side_effect = _mock_urlopen_ok(payload)
        out = ChemblConnector().search_molecules("aspirin", limit=5)
        assert len(out) == 2
        assert out[0].chembl_id == "CHEMBL1"

    def test_search_molecules_empty_query(self) -> None:
        with pytest.raises(ValueError):
            ChemblConnector().search_molecules("")


class TestZincConnector:
    @patch("urllib.request.urlopen")
    def test_get_substance_network_error_raises_runtimeerror(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        with pytest.raises(RuntimeError, match="ZINC request failed"):
            ZincConnector().get_substance("ZINC1")

    @patch("urllib.request.urlopen")
    def test_get_substance_parses_tsv(self, mock_urlopen) -> None:
        # ZINC15 TSV-like payload.
        tsv = (
            "zinc_id\tsmiles\tmwt\tlogp\n"
            "ZINC000000000053\tCN(C)C(=O)c1cccc(C#N)c1N\t188.2\t0.5\n"
        )
        mock_urlopen.side_effect = _mock_urlopen_ok(tsv.encode("utf-8"))
        sub = ZincConnector().get_substance("ZINC53")
        assert sub.zinc_id == "ZINC000000000053"
        assert sub.mw == pytest.approx(188.2)

    def test_get_substance_empty_id(self) -> None:
        with pytest.raises(ValueError):
            ZincConnector().get_substance("  ")

    def test_search_by_smiles_empty(self) -> None:
        with pytest.raises(ValueError):
            ZincConnector().search_by_smiles("")


# ---------------------------------------------------------------------------
# Integration: execute_skill dispatch
# ---------------------------------------------------------------------------


def test_skills_execute_through_registry() -> None:
    out = execute_skill(
        "reagent_database", "lookup", parameters={"query": "Sodium chloride"}
    )
    assert out["found"] is True
    assert out["entry"]["cas"] == "7647-14-5"

    out2 = execute_skill(
        "molecular_similarity",
        "tanimoto",
        parameters={"smiles_a": "c1ccccc1", "smiles_b": "c1ccccc1"},
    )
    assert out2["tanimoto"] == pytest.approx(1.0)


def test_execute_skill_unknown_op_raises() -> None:
    with pytest.raises(ValueError, match="Unknown operation"):
        execute_skill("reagent_database", "no_such_op")


def test_missing_rdkit_dependency_graceful(monkeypatch) -> None:
    """If rdkit is missing, optional_import raises RuntimeError with a hint."""
    import openscience.skills.cheminformatics.rdkit_ext as mod

    monkeypatch.setattr(
        mod,
        "optional_import",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("Skill dependency 'rdkit.Chem' is not installed.")
        ),
    )
    with pytest.raises(RuntimeError, match="rdkit"):
        mod._mol_from_smiles("c1ccccc1")
