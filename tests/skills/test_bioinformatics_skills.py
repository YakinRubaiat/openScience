"""Tests for the bioinformatics skill modules.

Each test exercises a skill's primary pure-python operation. Skills that
wrap external CLIs (cellranger, gatk, vep, macs2, homer, qiime2,
cellprofiler, fiji) are tested through their parse/summarize helpers or by
asserting the graceful RuntimeError when the binary is absent.
"""

from __future__ import annotations

import gzip
import shutil

import numpy as np
import pandas as pd
import pytest

from openscience.skills import execute_skill, get_skill
from openscience.skills import load_default_skills

load_default_skills()

SKILL_NAMES = [
    "networkx", "DESeq2", "seurat", "cellranger", "fastq_processing",
    "multiqc", "gseapy", "msigdb", "pathway_databases", "gatk", "vep",
    "macs2", "homer", "chromVAR", "minfi", "methylation_array", "qiime2",
    "dada2", "flowcore", "flowjo", "cellprofiler", "fiji", "maxquant",
    "proteomics_tools", "xcms", "metabolomics_tools",
]


def test_all_skills_registered():
    for name in SKILL_NAMES:
        assert get_skill(name) is not None, f"skill {name!r} not registered"


# --------------------------------------------------------------------- #
# networkx
# --------------------------------------------------------------------- #
def test_networkx_from_edges_and_centrality():
    edges = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "A"), ("A", "C")]
    r = execute_skill("networkx", "from_edges", edges=edges)
    assert r["n_nodes"] == 4 and r["n_edges"] == 5
    cent = execute_skill("networkx", "degree_centrality", edges=edges)
    top_nodes = {t["node"] for t in cent["top_nodes"]}
    assert {"A", "B", "C", "D"} == top_nodes
    pr = execute_skill("networkx", "pagerank", edges=edges)
    assert pr["n_nodes"] == 4
    bet = execute_skill("networkx", "betweenness", edges=edges)
    assert bet["n_nodes"] == 4


def test_networkx_communities_and_enrichment():
    edges = [("a", "b"), ("b", "c"), ("a", "c"), ("d", "e"), ("e", "f"), ("d", "f")]
    r = execute_skill("networkx", "communities", edges=edges)
    assert r["n_communities"] == 2
    assert r["modularity"] > 0.3
    enr = execute_skill(
        "networkx", "enrich_subnetwork",
        edges=edges, query_nodes=["a", "b", "c", "z"],
        subnetwork_nodes=["a", "b", "d"],
    )
    assert enr["overlap_size"] == 2
    assert 0.0 <= enr["p_value"] <= 1.0


# --------------------------------------------------------------------- #
# DESeq2
# --------------------------------------------------------------------- #
def _counts(seed=0):
    rng = np.random.default_rng(seed)
    base = rng.poisson(200, size=(200, 6))
    base[:20, 3:] = rng.poisson(600, size=(20, 3))  # 20 up-regulated genes
    return pd.DataFrame(
        base,
        index=[f"gene{i}" for i in range(200)],
        columns=["A1", "A2", "A3", "B1", "B2", "B3"],
    )


def test_deseq2_size_factors_and_normalize():
    counts = _counts()
    sf = execute_skill("DESeq2", "size_factors", counts=counts)
    assert len(sf["size_factors"]) == 6
    assert all(v > 0 for v in sf["size_factors"].values())
    norm = execute_skill("DESeq2", "normalize_counts", counts=counts)
    assert norm["n_genes"] == 200 and norm["n_samples"] == 6


def test_deseq2_differential_expression():
    counts = _counts()
    r = execute_skill(
        "DESeq2", "differential_expression",
        counts=counts, group_a=["A1", "A2", "A3"], group_b=["B1", "B2", "B3"],
        lfc_threshold=0.5,
    )
    assert r["n_genes_tested"] == 200
    assert r["n_significant"] >= 5
    top = r["top_genes"][0]
    assert top["log2FoldChange"] > 0  # up-regulated in B
    assert 0 <= top["padj"] <= 1


# --------------------------------------------------------------------- #
# seurat
# --------------------------------------------------------------------- #
def _adata():
    import anndata as ad

    rng = np.random.default_rng(1)
    x = rng.poisson(3.0, size=(40, 30)).astype(float)
    x[:20, :10] += 5  # cluster structure
    adata = ad.AnnData(x)
    adata.var_names = [f"gene{i}" for i in range(30)]
    adata.obs_names = [f"cell{i}" for i in range(40)]
    adata.obs["leiden"] = ["0"] * 20 + ["1"] * 20
    return adata


def test_seurat_recipe():
    adata = _adata()
    r = execute_skill("seurat", "normalize", data=adata)
    assert r["n_obs"] == 40
    hv = execute_skill("seurat", "find_variable_genes", data=adata, n_top_genes=10)
    assert hv["n_variable_genes"] == 10
    sc = execute_skill("seurat", "scale", data=adata)
    assert sc["mean_abs_scaled"] >= 0
    summary = execute_skill("seurat", "clusters_summary", data=adata)
    assert summary["n_clusters"] == 2
    assert summary["clusters"]["0"]["n_cells"] == 20
    assert len(summary["clusters"]["0"]["top_expressed_genes"]) == 5


# --------------------------------------------------------------------- #
# cellranger
# --------------------------------------------------------------------- #
def test_cellranger_summarize_metrics(tmp_path):
    csv = tmp_path / "metrics_summary.csv"
    csv.write_text(
        "Estimated Number of Cells,Mean Reads per Cell,Median Genes per Cell,Fraction Reads in Cells\n"
        "1,234,85,432,1,765,92.3%\n".replace(",", "\t").replace("\t", ",", 3)
    )
    # write a simple well-formed 2-row csv directly
    csv.write_text(
        "Estimated Number of Cells,Mean Reads per Cell,Median Genes per Cell,Sequencing Saturation\n"
        "1234,85432,1765,92.3%\n"
    )
    r = execute_skill("cellranger", "summarize_metrics", metrics_path=str(csv))
    assert r["estimated_cells"] == 1234.0
    assert r["mean_reads_per_cell"] == 85432.0
    assert r["n_metrics"] == 4


def test_cellranger_missing_binary_graceful(tmp_path):
    if shutil.which("cellranger"):
        pytest.skip("cellranger installed")
    with pytest.raises(RuntimeError, match="cellranger"):
        execute_skill(
            "cellranger", "count",
            id="s1", transcriptome="/ref", fastqs="/fq",
        )


# --------------------------------------------------------------------- #
# fastq_processing
# --------------------------------------------------------------------- #
def _write_fastq(path, n=6, gz=False):
    seq = "ACGTN" * 8
    qual = "IIIII" * 8  # Phred 40
    opener = gzip.open if gz else open
    with opener(path, "wt") as fh:
        for i in range(n):
            fh.write(f"@read{i}\n{seq}\n+\n{qual}\n")
    return path


def test_fastq_count_qc_peek(tmp_path):
    fq = _write_fastq(tmp_path / "reads.fastq", n=6)
    r = execute_skill("fastq_processing", "count_reads", fastq_path=str(fq))
    assert r["n_reads"] == 6
    qc = execute_skill("fastq_processing", "qc_stats", fastq_path=str(fq))
    assert qc["n_reads"] == 6
    assert qc["max_read_length"] == 40
    assert abs(qc["gc_percent"] - 40.0) < 0.01  # ACGTN -> 2/5 GC
    assert qc["mean_quality"] == pytest.approx(40.0)
    peek = execute_skill("fastq_processing", "peek", fastq_path=str(fq), n=3)
    assert peek["n_returned"] == 3
    assert peek["reads"][0]["id"] == "read0"


def test_fastq_gzip(tmp_path):
    fq = _write_fastq(tmp_path / "reads.fastq.gz", n=4, gz=True)
    r = execute_skill("fastq_processing", "count_reads", fastq_path=str(fq))
    assert r["n_reads"] == 4


# --------------------------------------------------------------------- #
# multiqc
# --------------------------------------------------------------------- #
def test_multiqc_aggregate_and_report(tmp_path):
    samples = {
        "s1": {"n_reads": 100, "mean_q": 38.0, "tool": "fastqc"},
        "s2": {"n_reads": 200, "mean_q": 36.5},
    }
    r = execute_skill("multiqc", "aggregate", samples=samples)
    assert r["n_samples"] == 2
    df = execute_skill("multiqc", "report_dataframe", samples=samples)
    assert df["n_metrics"] == 2
    assert set(df["metrics"]) == {"n_reads", "mean_q"}
    out = tmp_path / "report.csv"
    execute_skill("multiqc", "report_dataframe", samples=samples, output_path=str(out))
    assert out.exists()
    written = pd.read_csv(out)
    assert written.shape[0] == 2


# --------------------------------------------------------------------- #
# gseapy
# --------------------------------------------------------------------- #
def test_gseapy_enrich2_and_leading_edge():
    gene_sets = {
        "PATHWAY_A": [f"G{i}" for i in range(10)],
        "PATHWAY_B": [f"X{i}" for i in range(10)],
    }
    hit = ["G0", "G1", "G2", "G3", "G4"]
    r = execute_skill("gseapy", "enrich2", gene_list=hit, gene_sets=gene_sets)
    assert r["n_terms_tested"] == 2
    top = r["results"][0]
    assert top["term"] == "PATHWAY_A"
    assert top["overlap"] == 5
    le = execute_skill(
        "gseapy", "leading_edge",
        term="PATHWAY_A", ranked_genes=["G0", "G1", "Z9", "G2", "G3"],
        gene_sets=gene_sets,
    )
    assert le["n_leading_edge"] >= 1
    assert set(le["leading_edge_genes"]).issubset(set(hit))


def test_gseapy_prerank_missing_dependency_message():
    import importlib.util

    if importlib.util.find_spec("gseapy") is not None:
        pytest.skip("gseapy installed")
    with pytest.raises(RuntimeError, match="gseapy"):
        execute_skill(
            "gseapy", "prerank",
            ranked_genes={"G1": 1.0}, gene_sets={"S": ["G1"]},
        )


# --------------------------------------------------------------------- #
# msigdb
# --------------------------------------------------------------------- #
def _write_gmt(path):
    path.write_text(
        "HALL_A\tdesc A\tG1\tG2\tG3\tG4\tG5\n"
        "HALL_B\tdesc B\tG4\tG5\tG6\n"
        "HALL_C\tdesc C\tG7\tG8\tG9\tG10\tG11\tG12\tG13\tG14\n"
    )
    return path


def test_msigdb_load_and_filter(tmp_path):
    gmt = _write_gmt(tmp_path / "sets.gmt")
    r = execute_skill("msigdb", "load_gmt", gmt_path=str(gmt))
    assert r["n_gene_sets"] == 3
    assert r["gene_sets"]["HALL_A"] == ["G1", "G2", "G3", "G4", "G5"]
    assert r["max_size"] == 8
    f = execute_skill(
        "msigdb", "filter_gene_sets",
        gene_sets=r["gene_sets"], min_size=4, max_size=6,
    )
    assert f["n_kept"] == 1
    assert "HALL_A" in f["filtered_gene_sets"]


# --------------------------------------------------------------------- #
# pathway_databases
# --------------------------------------------------------------------- #
def test_pathway_databases(tmp_path):
    gmt = _write_gmt(tmp_path / "sets.gmt")
    r = execute_skill("pathway_databases", "load_pathways", gmt_path=str(gmt))
    assert r["n_pathways"] == 3
    s = execute_skill("pathway_databases", "pathway_summary", gmt_path=str(gmt))
    assert s["n_unique_genes"] == 14
    g = execute_skill(
        "pathway_databases", "genes_in_pathway",
        pathway="HALL_B", gmt_path=str(gmt), present_in=["G4", "G99"],
    )
    assert g["genes"] == ["G4"]
    d = execute_skill(
        "pathway_databases", "load_pathways",
        pathways={"P": ["a", "b"]},
    )
    assert d["source"] == "dict"


# --------------------------------------------------------------------- #
# gatk
# --------------------------------------------------------------------- #
def _write_vcf(path, with_csq=True):
    csq_header = (
        "##INFO=<ID=CSQ,Number=.,Type=String,Description=\"Consequence annotations. "
        "Format: Allele|Consequence|IMPACT|SYMBOL|Gene\">\n"
        if with_csq else ""
    )
    csq = "CSQ=T|missense_variant|MODERATE|GENE1|ENSG1,T|synonymous_variant|LOW|GENE2|ENSG2" if with_csq else "DP=30"
    path.write_text(
        "##fileformat=VCFv4.2\n"
        "##contig=<ID=chr1>\n"
        f"{csq_header}"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample1\n"
        f"chr1\t100\trs1\tA\tT\t50\tPASS\t{csq}\tGT\t0/1\n"
        "chr1\t200\trs2\tC\tG\t60\tPASS\tDP=10\tGT\t0/0\n"
    )
    return path


def test_gatk_index_validation(tmp_path):
    vcf = _write_vcf(tmp_path / "test.vcf")
    (tmp_path / "test.vcf.idx").touch()
    r = execute_skill("gatk", "index_validation", vcf_path=str(vcf))
    assert r["valid"] is True
    assert r["n_variants_seen"] == 2
    assert r["n_samples"] == 1
    assert r["index_found"] is True
    assert r["contigs"] == ["chr1"]


def test_gatk_missing_binary_graceful():
    if shutil.which("gatk"):
        pytest.skip("gatk installed")
    with pytest.raises(RuntimeError, match="gatk"):
        execute_skill("gatk", "haplotype_call", reference="r.fa", input_bam="x.bam", output_vcf="o.vcf")


# --------------------------------------------------------------------- #
# vep
# --------------------------------------------------------------------- #
def test_vep_parse_vcf_annotations(tmp_path):
    vcf = _write_vcf(tmp_path / "annotated.vcf")
    r = execute_skill("vep", "parse_vcf_annotations", vcf_path=str(vcf))
    assert r["n_variants_with_csq"] == 1
    assert "Allele" in r["csq_fields"]
    assert r["n_unique_genes"] >= 1
    assert r["consequence_counts"].get("missense_variant") == 1
    anns = r["annotations"]
    assert anns[0]["chrom"] == "chr1" and anns[0]["pos"] == 100


def test_vep_missing_binary_graceful():
    if shutil.which("vep"):
        pytest.skip("vep installed")
    with pytest.raises(RuntimeError, match="vep"):
        execute_skill("vep", "run", input_vcf="x.vcf", output_vcf="y.vcf")


# --------------------------------------------------------------------- #
# macs2
# --------------------------------------------------------------------- #
def _write_narrowpeak(path):
    path.write_text(
        "chr1\t100\t250\tpeak1\t500\t.\t12.5\t30.1\t25.2\t75\n"
        "chr1\t800\t950\tpeak2\t300\t.\t8.1\t20.4\t15.7\t60\n"
        "chr2\t50\t200\tpeak3\t700\t.\t15.2\t40.9\t35.1\t80\n"
    )
    return path


def test_macs2_parse_peaks_and_overlap(tmp_path):
    np_ = _write_narrowpeak(tmp_path / "peaks.narrowPeak")
    r = execute_skill("macs2", "parse_peaks", peaks_path=str(np_))
    assert r["n_peaks"] == 3
    assert r["mean_width"] == pytest.approx(150.0)
    assert set(r["chroms"]) == {"chr1", "chr2"}
    ov = execute_skill(
        "macs2", "summit_overlap",
        peaks_a=[{"chrom": "chr1", "start": 120, "end": 180},
                 {"chrom": "chr1", "start": 500, "end": 600}],
        peaks_b=[{"chrom": "chr1", "start": 100, "end": 150}],
    )
    assert ov["n_overlapping_a"] == 1
    assert ov["fraction_a_overlapping"] == pytest.approx(0.5)


def test_macs2_missing_binary_graceful():
    if shutil.which("macs2"):
        pytest.skip("macs2 installed")
    with pytest.raises(RuntimeError, match="macs2"):
        execute_skill("macs2", "callpeak", treatment="x.bam", genome_size="hs")


# --------------------------------------------------------------------- #
# homer
# --------------------------------------------------------------------- #
def test_homer_parse_motif_results(tmp_path):
    f = tmp_path / "knownResults.txt"
    f.write_text(
        "Motif Name\tConsensus\tP-value\tLog P-value\tq-value (Benjamini)\t# of Target Sequences with Motif\t% of Target Sequences with Motif\t# of Background Sequences with Motif\t% of Background Sequences with Motif\n"
        "STAT3(Stat)/IL4-STAT3\tGGAA\t1e-15\t-34.5\t1e-11\t30\t15.0%\t100\t5.0%\n"
        "PU.1(IRF)/ETS\tAAGGAA\t1e-9\t-20.0\t1e-6\t20\t10.0%\t150\t7.5%\n"
    )
    r = execute_skill("homer", "parse_motif_results", results_path=str(f))
    assert r["n_motifs"] == 2
    assert r["best_motif"].startswith("STAT3")
    assert r["top_motifs"][0]["p_value"] == pytest.approx(1e-15)
    assert r["top_motifs"][0]["target_percent"] == pytest.approx(15.0)


def test_homer_missing_binary_graceful():
    if shutil.which("findMotifsGenome.pl"):
        pytest.skip("homer installed")
    with pytest.raises(RuntimeError, match="HOMER"):
        execute_skill("homer", "find_motifs", peaks="p.bed", genome="hg38", output_dir="out")


# --------------------------------------------------------------------- #
# chromVAR
# --------------------------------------------------------------------- #
def test_chromvar_scores():
    rng = np.random.default_rng(2)
    mat = rng.poisson(5, (12, 6)).astype(float)
    mat[[0, 1, 2], :3] += 20  # first 3 cells boosted at motif peaks
    counts = pd.DataFrame(mat, index=[f"peak{i}" for i in range(12)],
                          columns=[f"cell{i}" for i in range(6)])
    r = execute_skill("chromVAR", "motif_bias_scores", counts=counts,
                      motif_matches=["peak0", "peak1", "peak2"])
    assert r["n_motif_peaks"] == 3
    zs = {s["cell"]: s["z_score"] for s in r["scores"]}
    assert zs["cell0"] > 0 and zs["cell5"] < 0
    dev = execute_skill(
        "chromVAR", "accessibility_deviation",
        counts=counts, motif_peak_sets={"MotifX": ["peak0", "peak1", "peak2"]},
    )
    cells = dev["motifs"]["MotifX"]["cells"]
    assert len(cells) == 6
    boosted = [c for c in cells if c["cell"] == "cell0"][0]
    assert boosted["deviation"] > 0


# --------------------------------------------------------------------- #
# minfi
# --------------------------------------------------------------------- #
def test_minfi_ops(tmp_path):
    csv = tmp_path / "idat.csv"
    pd.DataFrame(
        {"methylated": [800, 200, 500], "unmethylated": [200, 800, 500]},
        index=["cg1", "cg2", "cg3"],
    ).to_csv(csv)
    r = execute_skill("minfi", "read_idat_summary", csv_path=str(csv))
    assert r["n_probes"] == 3
    assert r["mean_beta"] == pytest.approx(0.5, abs=0.05)

    rng = np.random.default_rng(3)
    betas = pd.DataFrame(rng.random((20, 4)), columns=["s1", "s2", "s3", "s4"])
    dp = execute_skill("minfi", "detection_pvalues", betas=betas, threshold=0.8)
    assert dp["n_samples"] == 4
    assert all(0 <= v <= 1 for v in dp["fraction_above_threshold"].values())
    qn = execute_skill("minfi", "preprocess_normalize", betas=betas)
    after = list(qn["sample_means_after"].values())
    assert max(after) - min(after) < 0.05  # quantile-normalised -> close means


# --------------------------------------------------------------------- #
# methylation_array
# --------------------------------------------------------------------- #
def test_methylation_array():
    rng = np.random.default_rng(4)
    a = rng.beta(6, 1.5, size=(30, 3))  # higher in A
    b = rng.beta(1.5, 6, size=(30, 3))  # lower in B
    betas = pd.DataFrame(
        np.hstack([a, b]),
        index=[f"cg{i}" for i in range(30)],
        columns=["A1", "A2", "A3", "B1", "B2", "B3"],
    )
    m = execute_skill("methylation_array", "beta_to_m", betas=betas)
    assert m["n_samples"] == 6
    dmc = execute_skill(
        "methylation_array", "compute_dmc_regions",
        betas=betas, group_a=["A1", "A2", "A3"], group_b=["B1", "B2", "B3"],
        alpha=0.05, min_probes_per_region=2,
    )
    assert dmc["n_significant"] >= 5
    assert dmc["top_probes"][0]["delta_beta"] < 0  # B lower than A
    mds = execute_skill("methylation_array", "mds_plot_data", betas=betas)
    assert mds["n_samples"] == 6 and mds["n_components"] == 2
    assert len(mds["coordinates"]) == 6


# --------------------------------------------------------------------- #
# qiime2
# --------------------------------------------------------------------- #
def test_qiime2_parse_tsv_export(tmp_path):
    tsv = tmp_path / "table.tsv"
    tsv.write_text(
        "#OTU ID\tsampleA\tsampleB\tsampleC\n"
        "OTU1\t100\t0\t50\n"
        "OTU2\t0\t200\t25\n"
        "OTU3\t5\t5\t5\n"
    )
    r = execute_skill("qiime2", "parse_tsv_export", tsv_path=str(tsv))
    assert r["n_features"] == 3 and r["n_samples"] == 3
    assert r["total_counts_per_sample"]["sampleA"] == 105.0
    assert r["observed_features_per_sample"]["sampleB"] == 2


def test_qiime2_missing_binary_graceful():
    if shutil.which("qiime"):
        pytest.skip("qiime installed")
    with pytest.raises(RuntimeError, match="qiime"):
        execute_skill("qiime2", "import_data", input_path="in", output_path="out.qza", type="FeatureTable[Frequency]")


# --------------------------------------------------------------------- #
# dada2
# --------------------------------------------------------------------- #
def test_dada2_chimeras_diversity_rarefy():
    rng = np.random.default_rng(5)
    tab = pd.DataFrame(
        np.vstack([
            rng.poisson(500, (2, 4)),
            np.array([[1, 0, 1, 0], [2, 0, 0, 0], [1, 1, 0, 0]]),  # singletons/doubletons
        ]),
        index=[f"asv{i}" for i in range(5)],
        columns=["s1", "s2", "s3", "s4"],
    )
    r = execute_skill("dada2", "remove_chimeras", table=tab, return_table=True)
    assert r["n_chimeras_removed"] == 3
    assert r["n_features_out"] == 2
    div = execute_skill("dada2", "diversity", table=tab)
    assert set(div["per_sample"]["s1"]) >= {"shannon", "simpson", "observed_features"}
    assert div["per_sample"]["s1"]["observed_features"] == 5
    rar = execute_skill("dada2", "rarefy", table=tab, depth=400, seed=1, return_table=True)
    col_sums = pd.DataFrame(rar["table"]).sum(axis=0)
    assert all(abs(v - 400) < 1e-6 for v in col_sums)


# --------------------------------------------------------------------- #
# flowcore / flowjo
# --------------------------------------------------------------------- #
def test_flowcore_missing_dependency_message(tmp_path):
    import importlib.util

    if importlib.util.find_spec("flowio") or importlib.util.find_spec("fcsparser"):
        pytest.skip("FCS reader installed")
    fake = tmp_path / "sample.fcs"
    fake.write_bytes(b"FCS3.0 fake")
    with pytest.raises(RuntimeError, match="flowio"):
        execute_skill("flowcore", "load_fcs", fcs_path=str(fake))


def test_flowjo_parse_workspace_and_export(tmp_path):
    wsp = tmp_path / "exp.wsp"
    wsp.write_text(
        '<?xml version="1.0"?>\n'
        '<Workspace version="20.0">\n'
        '  <SampleList>\n'
        '    <Sample name="sample_A.fcs"><DataSet uri="file:///a.fcs"/></Sample>\n'
        '    <Sample name="sample_B.fcs"/>\n'
        '  </SampleList>\n'
        '  <Groups>\n'
        '    <GroupNode name="All Samples">\n'
        '      <Population name="Lymphocytes">\n'
        '        <Gate name="Singlet" parent="Lymphocytes"/>\n'
        '      </Population>\n'
        '    </GroupNode>\n'
        '  </Groups>\n'
        '</Workspace>\n'
    )
    r = execute_skill("flowjo", "parse_workspace", workspace_path=str(wsp))
    assert r["n_samples"] == 2
    assert "sample_A.fcs" in r["samples"]
    assert r["n_gates"] >= 1

    out = tmp_path / "events.csv"
    ev = execute_skill(
        "flowjo", "export_csv",
        events=[{"FSC-A": 100.0, "SSC-A": 50.0}, {"FSC-A": 110.0, "SSC-A": 55.0}],
        output_path=str(out),
    )
    assert ev["n_rows_written"] == 2
    assert out.exists()
    assert pd.read_csv(out).shape == (2, 2)


# --------------------------------------------------------------------- #
# cellprofiler
# --------------------------------------------------------------------- #
def test_cellprofiler_read_output_csv(tmp_path):
    csv = tmp_path / "objects.csv"
    pd.DataFrame(
        {
            "ImageNumber": [1, 1, 1, 2, 2, 2],
            "AreaShape_Area": [10, 12, 14, 30, 32, 28],
            "Intensity_Mean": [0.5, 0.6, 0.7, 1.5, 1.6, 1.4],
            "Label": ["a", "b", "c", "d", "e", "f"],
        }
    ).to_csv(csv, index=False)
    r = execute_skill("cellprofiler", "read_output_csv", csv_path=str(csv))
    assert r["n_rows"] == 6
    assert r["n_groups"] == 2
    assert r["objects_per_group"] == {"1": 3, "2": 3}
    feats = {f["feature"] for f in r["top_varying_features"]}
    assert "AreaShape_Area" in feats or "Intensity_Mean" in feats


def test_cellprofiler_missing_binary_graceful():
    if shutil.which("cellprofiler"):
        pytest.skip("cellprofiler installed")
    with pytest.raises(RuntimeError, match="cellprofiler"):
        execute_skill("cellprofiler", "run_pipeline", pipeline="p.cppipe")


# --------------------------------------------------------------------- #
# fiji
# --------------------------------------------------------------------- #
def test_fiji_measure_table(tmp_path):
    csv = tmp_path / "Results.csv"
    pd.DataFrame(
        {"Area": [10.0, 20.0, 30.0], "Mean": [100.0, 110.0, 120.0], "Label": ["a", "b", "c"]}
    ).to_csv(csv, index=False)
    r = execute_skill("fiji", "measure_table", csv_path=str(csv))
    assert r["n_measurements"] == 3
    assert r["stats"]["Area"]["mean"] == pytest.approx(20.0)
    assert r["stats"]["Mean"]["max"] == pytest.approx(120.0)
    assert r["total_area"] == pytest.approx(60.0)


def test_fiji_missing_binary_graceful():
    if any(shutil.which(n) for n in ("fiji", "ImageJ", "imagej")):
        pytest.skip("fiji installed")
    with pytest.raises(RuntimeError, match="Fiji"):
        execute_skill("fiji", "run_macro", macro="macro.ijm")


# --------------------------------------------------------------------- #
# maxquant
# --------------------------------------------------------------------- #
def _write_evidence(path):
    pd.DataFrame(
        {
            "Leading proteins": ["P1", "CON__P2", "REV__P3", "P4"],
            "Experiment": ["E1", "E1", "E2", "E2"],
            "Intensity": [1e6, 2e6, 3e6, 4e6],
            "PEP": [1e-4, 1e-3, 0.01, 1e-5],
            "Retention time": [10.0, 20.0, 30.0, 40.0],
        }
    ).to_csv(path, sep="\t", index=False)
    return path


def test_maxquant_read_evidence_and_contaminants(tmp_path):
    ev = _write_evidence(tmp_path / "evidence.txt")
    r = execute_skill("maxquant", "read_evidence", evidence_path=str(ev))
    assert r["n_rows"] == 4
    assert r["n_experiments"] == 2
    assert r["retention_time_range"] == [10.0, 40.0]
    flag = execute_skill("maxquant", "contaminants_flag", evidence_path=str(ev))
    assert flag["n_contaminants"] == 1
    assert flag["n_reverse"] == 1
    assert flag["n_flagged"] == 2
    out = tmp_path / "clean.txt"
    rm = execute_skill("maxquant", "contaminants_flag", evidence_path=str(ev), remove=True, output_path=str(out))
    assert rm["n_rows_clean"] == 2
    assert pd.read_csv(out, sep="\t").shape[0] == 2


def test_maxquant_lfq_summary(tmp_path):
    csv = tmp_path / "lfq.txt"
    pd.DataFrame(
        {
            "LFQ intensity 1": [100.0, 0.0, 300.0],
            "LFQ intensity 2": [200.0, 400.0, 0.0],
        }
    ).to_csv(csv, sep="\t", index=False)
    r = execute_skill("maxquant", "lfq_summary", evidence_path=str(csv))
    assert r["lfq_columns"] == ["LFQ intensity 1", "LFQ intensity 2"]
    assert r["lfq_medians"]["LFQ intensity 1"] == pytest.approx(200.0)


# --------------------------------------------------------------------- #
# proteomics_tools
# --------------------------------------------------------------------- #
def test_proteomics_tools():
    rng = np.random.default_rng(6)
    a = rng.lognormal(10, 0.2, size=(100, 3))
    b = rng.lognormal(10, 0.2, size=(100, 3))
    b[:15] *= 4  # up in B
    df = pd.DataFrame(
        np.hstack([a, b]),
        index=[f"prot{i}" for i in range(100)],
        columns=["A1", "A2", "A3", "B1", "B2", "B3"],
    )
    norm = execute_skill("proteomics_tools", "normalize_protein_intensities", intensities=df)
    assert len(norm["scaling_factors"]) == 6
    tt = execute_skill(
        "proteomics_tools", "ttest_proteins", intensities=df,
        group_a=["A1", "A2", "A3"], group_b=["B1", "B2", "B3"],
    )
    assert tt["n_significant"] >= 5
    volc = execute_skill(
        "proteomics_tools", "volcano_data", intensities=df,
        group_a=["A1", "A2", "A3"], group_b=["B1", "B2", "B3"],
    )
    assert volc["n_points"] == 100
    sig = [p for p in volc["points"] if p["significant"]]
    assert all(p["neg_log10_p"] > 0 for p in sig)


# --------------------------------------------------------------------- #
# xcms
# --------------------------------------------------------------------- #
def _features_frame():
    rng = np.random.default_rng(7)
    good = rng.lognormal(10, 0.1, size=(30, 6))
    bad = rng.lognormal(10, 2.0, size=(10, 6))  # noisy
    return pd.DataFrame(
        np.vstack([good, bad]),
        index=[f"feat{i}" for i in range(40)],
        columns=["A1", "A2", "A3", "B1", "B2", "B3"],
    )


def test_xcms_ops(tmp_path):
    df = _features_frame()
    csv = tmp_path / "features.csv"
    df.to_csv(csv)
    r = execute_skill("xcms", "read_features", features_path=str(csv))
    assert r["n_features"] == 40 and r["n_samples"] == 6
    rf = execute_skill("xcms", "rsd_filter", features=df, max_rsd=30.0, qc_samples=["A1", "A2", "A3"])
    assert rf["n_features_kept"] == 30
    tt = execute_skill(
        "xcms", "ttest_features", features=df,
        group_a=["A1", "A2", "A3"], group_b=["B1", "B2", "B3"],
    )
    assert tt["n_features_tested"] == 40
    assert 0 <= tt["top_features"][0]["padj"] <= 1


# --------------------------------------------------------------------- #
# metabolomics_tools
# --------------------------------------------------------------------- #
def _metabo_frame():
    rng = np.random.default_rng(8)
    x = rng.lognormal(9, 1.0, size=(50, 8))
    x[:10, 4:] *= 3
    return pd.DataFrame(x, columns=[f"S{i}" for i in range(8)])


def test_metabolomics_tools(tmp_path):
    df = _metabo_frame()
    tic = execute_skill("metabolomics_tools", "tics_normalize", data=df)
    vals = np.array(list(tic["scaling_factors"].values()))
    assert np.all(vals > 0)
    pca = execute_skill("metabolomics_tools", "pca_scores", data=df, n_components=2)
    assert pca["n_components"] == 2
    assert len(pca["scores"]) == 8
    pls = execute_skill(
        "metabolomics_tools", "plsda_scores",
        data=df, labels=["ctrl"] * 4 + ["treated"] * 4,
    )
    assert pls["training_accuracy"] == 1.0
    assert pls["classes"] == ["ctrl", "treated"]
    assert len(pls["scores"]) == 8
    for score in pls["scores"]:
        assert "LV1" in score and "class" in score
