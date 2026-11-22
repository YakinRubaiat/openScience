#!/usr/bin/env python3
"""Generate agent files with proper class implementations."""

import os
from pathlib import Path

AGENTS = {
    # Literature Review Agents (15)
    "literature": [
        ("pubmed_search", "PubMed/PMC systematic literature search", "pubmed_api", "xml_parsing", "search_query", "paper_list"),
        ("biorxiv_monitor", "Preprint tracking and notifications", "biorxiv_api", "rss_parsing", "search_terms", "preprint_list"),
        ("semantic_scholar", "Citation network analysis", "semantic_scholar_api", "network_analysis", "paper_id", "citation_graph"),
        ("pubmed_central", "Full-text article mining", "pmc_api", "fulltext_parser", "query", "fulltext_data"),
        ("clinical_trials", "Clinical trial registry search", "clinicaltrials_api", "trial_parser", "condition", "trial_list"),
        ("patent_search", "USPTO/EPO patent literature", "patent_api", "patent_parser", "invention_query", "patent_list"),
        ("openalex", "Open bibliographic database", "openalex_api", "bibliometric_analysis", "query", "work_list"),
        ("lit_summarizer", "Automated literature summarization", "llm_summarization", "citation_extraction", "paper_text", "summary"),
        ("citation_graph", "Citation network visualization", "networkx", "graph_visualization", "citation_data", "network_graph"),
        ("systematic_review", "PRISMA-compliant review automation", "prisma_workflow", "screening_automation", "search_results", "prisma_flow"),
        ("meta_analysis", "Meta-analysis and forest plots", "statsmodels_meta", "forest_plot", "effect_sizes", "meta_analysis_results"),
        ("fact_checker", "Claim verification against sources", "crossref_api", "fact_verification", "claims", "verification_report"),
        ("related_work_finder", "Similar research identification", "semantic_similarity", "paper_clustering", "target_paper", "similar_papers"),
        ("research_gap_analyzer", "Identification of understudied areas", "bibliometric_analysis", "topic_modeling", "corpus", "gap_analysis"),
        ("trend_tracker", "Emerging topic detection", "topic_modeling", "trend_detection", "time_series_papers", "trend_report"),
    ],
    # Experiment Planning Agents (15)
    "experiment": [
        ("power_analysis", "Statistical power calculation", "statsmodels", "numpy_stats", "effect_size", "sample_size"),
        ("experimental_design", "Factorial and response surface designs", "pyDOE2", "design_of_experiments", "factors", "design_matrix"),
        ("sample_size_calc", "Sample size determination", "statsmodels", "power_analysis", "parameters", "sample_size"),
        ("protocol_optimizer", "Experimental protocol optimization", "bayesian_optimization", "protocol_analysis", "protocol_parameters", "optimized_protocol"),
        ("reagent_optimizer", "Reagent selection and concentration", "optimization_algorithms", "reagent_database", "reaction_conditions", "optimal_reagents"),
        ("control_designer", "Positive/negative control selection", "control_theory", "experimental_design", "experiment_parameters", "control_plan"),
        ("randomization_planner", "Randomization and blinding schemes", "randomization_algorithms", "blinding_protocols", "study_design", "randomization_plan"),
        ("batch_effect_guardian", "Batch effect detection and correction planning", "combat", "batch_effect_detection", "batch_metadata", "correction_plan"),
        ("dose_response_design", "Dose-response curve optimization", "dose_response_analysis", "curve_fitting", "dose_range", "optimal_doses"),
        ("time_course_planner", "Longitudinal study design", "time_series_design", "longitudinal_analysis", "study_duration", "time_points"),
        ("multiplex_designer", "Multiplex assay panel design", "multiplex_optimization", "assay_compatibility", "target_list", "multiplex_panel"),
        ("feasibility_checker", "Resource and timeline feasibility", "resource_planning", "timeline_estimation", "project_scope", "feasibility_report"),
        ("cost_estimator", "Budget and cost projection", "cost_modeling", "budget_optimization", "resource_requirements", "cost_breakdown"),
        ("risk_assessor", "Technical risk identification", "risk_analysis", "mitigation_planning", "project_plan", "risk_assessment"),
        ("preregistration_writer", "Preregistration document drafting", "preregistration_templates", "study_design_documentation", "study_plan", "preregistration_doc"),
    ],
    # Data Management Agents (15)
    "data_management": [
        ("data_ingestor", "Multi-format data import", "pandas", "bioio", "file_path", "loaded_data"),
        ("format_converter", "File format conversion", "format_converters", "data_validation", "source_format", "converted_data"),
        ("metadata_extractor", "Metadata extraction and validation", "metadata_standards", "validation_rules", "raw_data", "metadata"),
        ("data_validator", "Quality and integrity checking", "data_validation", "integrity_checks", "dataset", "validation_report"),
        ("data_cleaner", "Outlier detection and cleaning", "outlier_detection", "cleaning_algorithms", "dirty_data", "clean_data"),
        ("normalization_expert", "Normalization method selection", "normalization_methods", "data_characteristics", "raw_data", "normalized_data"),
        ("batch_corrector", "Batch effect correction", "harmony", "combat", "batched_data", "corrected_data"),
        ("data_integrator", "Multi-omics data integration", "multiomics_integration", "data_alignment", "omics_datasets", "integrated_data"),
        ("database_writer", "Database ingestion", "database_connectors", "schema_management", "data", "database_records"),
        ("s3_manager", "Cloud storage management", "boto3", "cloud_storage", "local_files", "cloud_locations"),
        ("version_controller", "Data versioning and lineage", "dvc", "lineage_tracking", "data", "versioned_data"),
        ("privacy_guardian", "PHI/PII detection and masking", "pii_detection", "anonymization", "sensitive_data", "masked_data"),
        ("compression_optimizer", "Storage optimization", "compression_algorithms", "storage_optimization", "data", "compressed_data"),
        ("backup_manager", "Backup and archival", "backup_strategies", "archival_systems", "data", "backup_locations"),
        ("provenance_tracker", "Complete data lineage tracking", "provenance_modeling", "workflow_tracking", "pipeline_steps", "provenance_graph"),
    ],
    # Analysis Agents (20)
    "analysis": [
        ("qc_analyzer", "Quality control metrics", "scanpy", "multiqc", "raw_data", "qc_report"),
        ("deseq2_specialist", "Bulk RNA-seq differential expression", "DESeq2", "rpy2", "count_matrix", "de_results"),
        ("scanpy_specialist", "Single-cell analysis (Scanpy)", "scanpy", "anndata", "h5ad_file", "analysis_results"),
        ("seurat_specialist", "Single-cell analysis (Seurat)", "seurat", "rpy2", "seurat_object", "analysis_results"),
        ("cellranger_specialist", "10x Genomics preprocessing", "cellranger", "fastq_processing", "fastq_files", "count_matrix"),
        ("gsea_analyzer", "Gene set enrichment analysis", "gseapy", "msigdb", "gene_list", "enrichment_results"),
        ("pathway_analyzer", "Pathway and network analysis", "pathway_databases", "network_analysis", "gene_list", "pathway_results"),
        ("variant_caller", "Variant detection and annotation", "gatk", "vep", "bam_files", "vcf_file"),
        ("chip_seq_analyzer", "ChIP-seq peak calling and analysis", "macs2", "homer", "chip_bam", "peak_calls"),
        ("atac_seq_analyzer", "ATAC-seq analysis", "macs2", "chromVAR", "atac_bam", "accessibility_results"),
        ("methylation_analyzer", "DNA methylation analysis", "minfi", "methylation_array", "idat_files", "methylation_data"),
        ("metagenomics_analyzer", "Microbiome analysis", "qiime2", "dada2", "fastq_files", "microbiome_profile"),
        ("proteomics_analyzer", "Mass spec proteomics", "maxquant", "proteomics_tools", "raw_files", "protein_quant"),
        ("metabolomics_analyzer", "Metabolomics data analysis", "xcms", "metabolomics_tools", "mzml_files", "metabolite_data"),
        ("image_analyzer", "Bioimage analysis (CellProfiler, Fiji)", "cellprofiler", "fiji", "images", "measurements"),
        ("flow_cytometry_analyzer", "Flow cytometry gating and analysis", "flowcore", "flowjo", "fcs_files", "gating_results"),
        ("ml_modeler", "Machine learning model development", "scikit-learn", "model_training", "features", "trained_model"),
        ("deep_learning_specialist", "Neural network design and training", "pytorch", "tensorflow", "training_data", "model_weights"),
        ("statistical_modeler", "Statistical inference and modeling", "statsmodels", "bayesian_inference", "data", "model_results"),
        ("survival_analyzer", "Survival analysis and Kaplan-Meier", "lifelines", "survival_analysis", "survival_data", "km_curves"),
    ],
    # Visualization Agents (15)
    "visualization": [
        ("matplotlib_stylist", "Matplotlib figure optimization", "matplotlib", "style_sheets", "figure", "optimized_figure"),
        ("seaborn_stylist", "Statistical visualization", "seaborn", "statistical_plots", "data", "statistical_plots"),
        ("plotly_specialist", "Interactive visualizations", "plotly", "interactive_viz", "data", "interactive_plot"),
        ("ggplot_converter", "R ggplot2 to Python conversion", "plotnine", "ggplot_syntax", "r_code", "python_plot"),
        ("publication_formatter", "Journal-specific formatting", "publication_styles", "journal_templates", "figure", "formatted_figure"),
        ("color_palette_designer", "Accessible color scheme design", "colorbrewer", "accessibility_checking", "plot_type", "color_palette"),
        ("layout_composer", "Multi-panel figure composition", "matplotlib_gridspec", "layout_optimization", "figures", "composed_figure"),
        ("annotation_specialist", "Figure annotation and labeling", "annotation_tools", "label_placement", "figure", "annotated_figure"),
        ("vector_graphics_editor", "SVG/PDF optimization", "cairosvg", "vector_editing", "svg_file", "optimized_svg"),
        ("data_viz_consultant", "Visualization best practices", "viz_guidelines", "chart_selection", "data_type", "viz_recommendations"),
        ("interactive_dashboard", "Web-based dashboard creation", "dash", "plotly_dash", "data", "dashboard_app"),
        ("animation_generator", "Animated figure creation", "matplotlib_animation", "ffmpeg", "time_series_data", "animation"),
        ("3d_visualizer", "3D structure visualization", "py3Dmol", "nglview", "pdb_structure", "3d_visualization"),
        ("graph_network_visualizer", "Network and graph visualization", "networkx", "graphviz", "network_data", "network_graph"),
        ("schematic_illustrator", "Scientific schematic creation", "matplotlib", "illustration_tools", "description", "schematic"),
    ],
    # Writing Agents (20)
    "writing": [
        ("abstract_writer", "Abstract drafting and optimization", "text_summarization", "scientific_writing", "paper_content", "abstract_draft"),
        ("introduction_writer", "Introduction section drafting", "scientific_writing", "literature_review", "research_background", "introduction"),
        ("methods_writer", "Methods section documentation", "methodology_writing", "protocol_documentation", "methods_details", "methods_section"),
        ("results_writer", "Results narrative generation", "results_writing", "statistical_reporting", "analysis_results", "results_section"),
        ("discussion_writer", "Discussion and interpretation", "discussion_writing", "scientific_argumentation", "results_context", "discussion_section"),
        ("conclusion_writer", "Conclusion and future directions", "conclusion_writing", "future_work_synthesis", "study_summary", "conclusion"),
        ("citation_manager", "Reference formatting and management", "bibtex", "citation_styles", "references", "formatted_citations"),
        ("bibtex_converter", "BibTeX conversion and validation", "bibtex_parsing", "citation_validation", "citations", "bibtex_file"),
        ("journal_formatter", "Journal-specific submission formatting", "journal_templates", "formatting_rules", "manuscript", "formatted_manuscript"),
        ("cover_letter_writer", "Cover letter drafting", "letter_writing", "submission_guidelines", "manuscript_summary", "cover_letter"),
        ("response_to_reviewers", "Reviewer response drafting", "response_writing", "revision_planning", "reviewer_comments", "response_letter"),
        ("grant_proposal_writer", "Grant proposal development", "grant_writing", "budget_planning", "research_plan", "grant_proposal"),
        ("specific_aims_optimizer", "Specific aims refinement", "aims_optimization", "logic_modeling", "research_objectives", "refined_aims"),
        ("lay_summary_writer", "Plain language summary", "science_communication", "plain_language", "technical_content", "lay_summary"),
        ("press_release_writer", "Media and outreach materials", "press_writing", "media_relations", "research_highlights", "press_release"),
        ("thesis_writer", "Thesis and dissertation drafting", "thesis_structure", "academic_writing", "research_content", "thesis_chapters"),
        ("presentation_writer", "Conference presentation materials", "presentation_design", "slide_creation", "research_content", "presentation_slides"),
        ("poster_creator", "Scientific poster design", "poster_layout", "visual_communication", "research_summary", "poster_file"),
        ("protocol_writer", "Standard operating procedures", "protocol_documentation", "sop_writing", "protocol_steps", "sop_document"),
        ("dataset_descriptor", "Data availability statements", "data_description", "repository_documentation", "dataset_metadata", "availability_statement"),
    ],
}


def create_agent_class(category, name, description, skill1, skill2, input_type, output_type):
    """Generate agent class code."""
    class_name = "".join(word.title() for word in name.split("_")) + "Agent"
    
    template = f'''"""{description} agent."""

from openscience.core.agent import BaseAgent, AgentMetadata


class {class_name}(BaseAgent):
    """Agent for {description.lower()}."""

    metadata = AgentMetadata(
        name="{name}",
        category="{category}",
        description="{description}",
        required_skills=["{skill1}", "{skill2}"],
        input_types=["{input_type}"],
        output_types=["{output_type}"],
    )

    async def execute(self, task, context):
        """Execute {name} analysis."""
        data = task.parameters.get("input_data")

        result = await self.run_skill(
            "{skill1}",
            operation="process",
            data=data,
        )

        return self.format_result(result)
'''
    return template


def main():
    """Generate all agent files."""
    base_dir = Path("openScience/src/openscience/agents")
    
    for category, agents in AGENTS.items():
        category_dir = base_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        for name, desc, skill1, skill2, input_type, output_type in agents:
            file_path = category_dir / f"{name}.py"
            code = create_agent_class(category, name, desc, skill1, skill2, input_type, output_type)
            file_path.write_text(code)
            print(f"Created: {file_path}")
    
    print(f"\n✅ Generated {sum(len(a) for a in AGENTS.values())} agent files")


if __name__ == "__main__":
    main()
