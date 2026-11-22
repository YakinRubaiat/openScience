# Agent Catalog

This document provides a complete catalog of all 111 specialized agents in openScience.

## Review Agents (11)

### security_reviewer
**Category**: Review  
**Description**: Reviews code for security vulnerabilities and OWASP compliance  
**Skills**: bandit, safety, semgrep  
**Input**: source_code, dependencies  
**Output**: security_report, vulnerability_list, recommendations

### code_quality_reviewer
**Category**: Review  
**Description**: Reviews code quality, style, and maintainability  
**Skills**: pylint, radon, black, mypy  
**Input**: source_code  
**Output**: quality_report, complexity_metrics, recommendations

### architecture_reviewer
**Category**: Review  
**Description**: Reviews software architecture and design patterns  
**Skills**: pydeps, import-linter, architecture-rules  
**Input**: source_code, dependencies  
**Output**: architecture_report, dependency_graph, recommendations

### performance_reviewer
**Category**: Review  
**Description**: Reviews code performance and identifies optimizations  
**Skills**: py-spy, memory-profiler, line-profiler, scalene  
**Input**: source_code, runtime_metrics  
**Output**: performance_report, bottlenecks, recommendations

### documentation_reviewer
**Category**: Review  
**Description**: Reviews documentation completeness and quality  
**Skills**: pydocstyle, darglint, interrogate  
**Input**: source_code, documentation  
**Output**: documentation_report, coverage_metrics, recommendations

### test_coverage_reviewer
**Category**: Review  
**Description**: Reviews test coverage and quality  
**Skills**: pytest, coverage, mutmut  
**Input**: test_code, coverage_reports  
**Output**: coverage_report, test_quality_metrics, recommendations

### database_reviewer
**Category**: Review  
**Description**: Reviews database design and query optimization  
**Skills**: sqlfluff, pgbadger, django-debug-toolbar  
**Input**: models, migrations, queries  
**Output**: database_report, optimization_suggestions, recommendations

### api_design_reviewer
**Category**: Review  
**Description**: Reviews API design and RESTful best practices  
**Skills**: openapi-spec-validator, spectral  
**Input**: api_spec, endpoint_code  
**Output**: api_report, design_violations, recommendations

### dependency_reviewer
**Category**: Review  
**Description**: Reviews dependency management and security  
**Skills**: safety, pip-audit, license-checker, pipdeptree  
**Input**: requirements_files, lock_files  
**Output**: dependency_report, vulnerability_list, recommendations

### accessibility_reviewer
**Category**: Review  
**Description**: Reviews accessibility compliance and WCAG standards  
**Skills**: axe-core, pa11y, html-proofer  
**Input**: html_files, ui_components  
**Output**: accessibility_report, wcag_violations, recommendations

### devops_reviewer
**Category**: Review  
**Description**: Reviews DevOps practices and infrastructure configuration  
**Skills**: hadolint, trivy, checkov, kube-score  
**Input**: dockerfiles, ci_configs, infrastructure_code  
**Output**: devops_report, security_findings, recommendations

---

## Literature Review Agents (15)

### pubmed_search
**Category**: Literature Review  
**Description**: PubMed/PMC systematic literature search  
**Skills**: pubmed_api, xml_parsing  
**Input**: search_query, date_range  
**Output**: paper_list, abstracts, citations

### biorxiv_monitor
**Category**: Literature Review  
**Description**: Preprint tracking and notifications  
**Skills**: biorxiv_api, rss_parsing  
**Input**: search_terms  
**Output**: preprint_list

### semantic_scholar
**Category**: Literature Review  
**Description**: Citation network analysis  
**Skills**: semantic_scholar_api, network_analysis  
**Input**: paper_id  
**Output**: citation_graph

### pubmed_central
**Category**: Literature Review  
**Description**: Full-text article mining  
**Skills**: pmc_api, fulltext_parser  
**Input**: query  
**Output**: fulltext_data

### clinical_trials
**Category**: Literature Review  
**Description**: Clinical trial registry search  
**Skills**: clinicaltrials_api, trial_parser  
**Input**: condition  
**Output**: trial_list

### patent_search
**Category**: Literature Review  
**Description**: USPTO/EPO patent literature  
**Skills**: patent_api, patent_parser  
**Input**: invention_query  
**Output**: patent_list

### openalex
**Category**: Literature Review  
**Description**: Open bibliographic database  
**Skills**: openalex_api, bibliometric_analysis  
**Input**: query  
**Output**: work_list

### lit_summarizer
**Category**: Literature Review  
**Description**: Automated literature summarization  
**Skills**: llm_summarization, citation_extraction  
**Input**: paper_text  
**Output**: summary

### citation_graph
**Category**: Literature Review  
**Description**: Citation network visualization  
**Skills**: networkx, graph_visualization  
**Input**: citation_data  
**Output**: network_graph

### systematic_review
**Category**: Literature Review  
**Description**: PRISMA-compliant review automation  
**Skills**: prisma_workflow, screening_automation  
**Input**: search_results  
**Output**: prisma_flow

### meta_analysis
**Category**: Literature Review  
**Description**: Meta-analysis and forest plots  
**Skills**: statsmodels_meta, forest_plot  
**Input**: effect_sizes  
**Output**: meta_analysis_results

### fact_checker
**Category**: Literature Review  
**Description**: Claim verification against sources  
**Skills**: crossref_api, fact_verification  
**Input**: claims  
**Output**: verification_report

### related_work_finder
**Category**: Literature Review  
**Description**: Similar research identification  
**Skills**: semantic_similarity, paper_clustering  
**Input**: target_paper  
**Output**: similar_papers

### research_gap_analyzer
**Category**: Literature Review  
**Description**: Identification of understudied areas  
**Skills**: bibliometric_analysis, topic_modeling  
**Input**: corpus  
**Output**: gap_analysis

### trend_tracker
**Category**: Literature Review  
**Description**: Emerging topic detection  
**Skills**: topic_modeling, trend_detection  
**Input**: time_series_papers  
**Output**: trend_report

---

## Experiment Planning Agents (15)

### power_analysis
**Category**: Experiment Planning  
**Description**: Statistical power calculation  
**Skills**: statsmodels, numpy_stats  
**Input**: effect_size, alpha, power_target  
**Output**: sample_size, power_curve

### experimental_design
**Category**: Experiment Planning  
**Description**: Factorial and response surface designs  
**Skills**: pyDOE2, design_of_experiments  
**Input**: factors  
**Output**: design_matrix

### sample_size_calc
**Category**: Experiment Planning  
**Description**: Sample size determination  
**Skills**: statsmodels, power_analysis  
**Input**: parameters  
**Output**: sample_size

### protocol_optimizer
**Category**: Experiment Planning  
**Description**: Experimental protocol optimization  
**Skills**: bayesian_optimization, protocol_analysis  
**Input**: protocol_parameters  
**Output**: optimized_protocol

### reagent_optimizer
**Category**: Experiment Planning  
**Description**: Reagent selection and concentration  
**Skills**: optimization_algorithms, reagent_database  
**Input**: reaction_conditions  
**Output**: optimal_reagents

### control_designer
**Category**: Experiment Planning  
**Description**: Positive/negative control selection  
**Skills**: control_theory, experimental_design  
**Input**: experiment_parameters  
**Output**: control_plan

### randomization_planner
**Category**: Experiment Planning  
**Description**: Randomization and blinding schemes  
**Skills**: randomization_algorithms, blinding_protocols  
**Input**: study_design  
**Output**: randomization_plan

### batch_effect_guardian
**Category**: Experiment Planning  
**Description**: Batch effect detection and correction planning  
**Skills**: combat, batch_effect_detection  
**Input**: batch_metadata  
**Output**: correction_plan

### dose_response_design
**Category**: Experiment Planning  
**Description**: Dose-response curve optimization  
**Skills**: dose_response_analysis, curve_fitting  
**Input**: dose_range  
**Output**: optimal_doses

### time_course_planner
**Category**: Experiment Planning  
**Description**: Longitudinal study design  
**Skills**: time_series_design, longitudinal_analysis  
**Input**: study_duration  
**Output**: time_points

### multiplex_designer
**Category**: Experiment Planning  
**Description**: Multiplex assay panel design  
**Skills**: multiplex_optimization, assay_compatibility  
**Input**: target_list  
**Output**: multiplex_panel

### feasibility_checker
**Category**: Experiment Planning  
**Description**: Resource and timeline feasibility  
**Skills**: resource_planning, timeline_estimation  
**Input**: project_scope  
**Output**: feasibility_report

### cost_estimator
**Category**: Experiment Planning  
**Description**: Budget and cost projection  
**Skills**: cost_modeling, budget_optimization  
**Input**: resource_requirements  
**Output**: cost_breakdown

### risk_assessor
**Category**: Experiment Planning  
**Description**: Technical risk identification  
**Skills**: risk_analysis, mitigation_planning  
**Input**: project_plan  
**Output**: risk_assessment

### preregistration_writer
**Category**: Experiment Planning  
**Description**: Preregistration document drafting  
**Skills**: preregistration_templates, study_design_documentation  
**Input**: study_plan  
**Output**: preregistration_doc

---

## Data Management Agents (15)

### data_ingestor
**Category**: Data Management  
**Description**: Multi-format data import  
**Skills**: pandas, bioio  
**Input**: file_path, format_hint  
**Output**: loaded_data

### format_converter
**Category**: Data Management  
**Description**: File format conversion  
**Skills**: format_converters, data_validation  
**Input**: source_format  
**Output**: converted_data

### metadata_extractor
**Category**: Data Management  
**Description**: Metadata extraction and validation  
**Skills**: metadata_standards, validation_rules  
**Input**: raw_data  
**Output**: metadata

### data_validator
**Category**: Data Management  
**Description**: Quality and integrity checking  
**Skills**: data_validation, integrity_checks  
**Input**: dataset  
**Output**: validation_report

### data_cleaner
**Category**: Data Management  
**Description**: Outlier detection and cleaning  
**Skills**: outlier_detection, cleaning_algorithms  
**Input**: dirty_data  
**Output**: clean_data

### normalization_expert
**Category**: Data Management  
**Description**: Normalization method selection  
**Skills**: normalization_methods, data_characteristics  
**Input**: raw_data  
**Output**: normalized_data

### batch_corrector
**Category**: Data Management  
**Description**: Batch effect correction  
**Skills**: harmony, combat  
**Input**: batched_data  
**Output**: corrected_data

### data_integrator
**Category**: Data Management  
**Description**: Multi-omics data integration  
**Skills**: multiomics_integration, data_alignment  
**Input**: omics_datasets  
**Output**: integrated_data

### database_writer
**Category**: Data Management  
**Description**: Database ingestion  
**Skills**: database_connectors, schema_management  
**Input**: data  
**Output**: database_records

### s3_manager
**Category**: Data Management  
**Description**: Cloud storage management  
**Skills**: boto3, cloud_storage  
**Input**: local_files  
**Output**: cloud_locations

### version_controller
**Category**: Data Management  
**Description**: Data versioning and lineage  
**Skills**: dvc, lineage_tracking  
**Input**: data  
**Output**: versioned_data

### privacy_guardian
**Category**: Data Management  
**Description**: PHI/PII detection and masking  
**Skills**: pii_detection, anonymization  
**Input**: sensitive_data  
**Output**: masked_data

### compression_optimizer
**Category**: Data Management  
**Description**: Storage optimization  
**Skills**: compression_algorithms, storage_optimization  
**Input**: data  
**Output**: compressed_data

### backup_manager
**Category**: Data Management  
**Description**: Backup and archival  
**Skills**: backup_strategies, archival_systems  
**Input**: data  
**Output**: backup_locations

### provenance_tracker
**Category**: Data Management  
**Description**: Complete data lineage tracking  
**Skills**: provenance_modeling, workflow_tracking  
**Input**: pipeline_steps  
**Output**: provenance_graph

---

## Data Analysis Agents (20)

### qc_analyzer
**Category**: Data Analysis  
**Description**: Quality control metrics  
**Skills**: scanpy, multiqc  
**Input**: raw_data  
**Output**: qc_report

### deseq2_specialist
**Category**: Data Analysis  
**Description**: Bulk RNA-seq differential expression  
**Skills**: DESeq2, rpy2  
**Input**: count_matrix  
**Output**: de_results

### scanpy_specialist
**Category**: Data Analysis  
**Description**: Single-cell analysis (Scanpy)  
**Skills**: scanpy, anndata  
**Input**: h5ad_file  
**Output**: analysis_results

### seurat_specialist
**Category**: Data Analysis  
**Description**: Single-cell analysis (Seurat)  
**Skills**: seurat, rpy2  
**Input**: seurat_object  
**Output**: analysis_results

### cellranger_specialist
**Category**: Data Analysis  
**Description**: 10x Genomics preprocessing  
**Skills**: cellranger, fastq_processing  
**Input**: fastq_files  
**Output**: count_matrix

### gsea_analyzer
**Category**: Data Analysis  
**Description**: Gene set enrichment analysis  
**Skills**: gseapy, msigdb  
**Input**: gene_list  
**Output**: enrichment_results

### pathway_analyzer
**Category**: Data Analysis  
**Description**: Pathway and network analysis  
**Skills**: pathway_databases, network_analysis  
**Input**: gene_list  
**Output**: pathway_results

### variant_caller
**Category**: Data Analysis  
**Description**: Variant detection and annotation  
**Skills**: gatk, vep  
**Input**: bam_files  
**Output**: vcf_file

### chip_seq_analyzer
**Category**: Data Analysis  
**Description**: ChIP-seq peak calling and analysis  
**Skills**: macs2, homer  
**Input**: chip_bam  
**Output**: peak_calls

### atac_seq_analyzer
**Category**: Data Analysis  
**Description**: ATAC-seq analysis  
**Skills**: macs2, chromVAR  
**Input**: atac_bam  
**Output**: accessibility_results

### methylation_analyzer
**Category**: Data Analysis  
**Description**: DNA methylation analysis  
**Skills**: minfi, methylation_array  
**Input**: idat_files  
**Output**: methylation_data

### metagenomics_analyzer
**Category**: Data Analysis  
**Description**: Microbiome analysis  
**Skills**: qiime2, dada2  
**Input**: fastq_files  
**Output**: microbiome_profile

### proteomics_analyzer
**Category**: Data Analysis  
**Description**: Mass spec proteomics  
**Skills**: maxquant, proteomics_tools  
**Input**: raw_files  
**Output**: protein_quant

### metabolomics_analyzer
**Category**: Data Analysis  
**Description**: Metabolomics data analysis  
**Skills**: xcms, metabolomics_tools  
**Input**: mzml_files  
**Output**: metabolite_data

### image_analyzer
**Category**: Data Analysis  
**Description**: Bioimage analysis (CellProfiler, Fiji)  
**Skills**: cellprofiler, fiji  
**Input**: images  
**Output**: measurements

### flow_cytometry_analyzer
**Category**: Data Analysis  
**Description**: Flow cytometry gating and analysis  
**Skills**: flowcore, flowjo  
**Input**: fcs_files  
**Output**: gating_results

### ml_modeler
**Category**: Data Analysis  
**Description**: Machine learning model development  
**Skills**: scikit-learn, model_training  
**Input**: features  
**Output**: trained_model

### deep_learning_specialist
**Category**: Data Analysis  
**Description**: Neural network design and training  
**Skills**: pytorch, tensorflow  
**Input**: training_data  
**Output**: model_weights

### statistical_modeler
**Category**: Data Analysis  
**Description**: Statistical inference and modeling  
**Skills**: statsmodels, bayesian_inference  
**Input**: data  
**Output**: model_results

### survival_analyzer
**Category**: Data Analysis  
**Description**: Survival analysis and Kaplan-Meier  
**Skills**: lifelines, survival_analysis  
**Input**: survival_data  
**Output**: km_curves

---

## Figure Generation Agents (15)

### matplotlib_stylist
**Category**: Figure Generation  
**Description**: Matplotlib figure optimization  
**Skills**: matplotlib, style_sheets  
**Input**: figure  
**Output**: optimized_figure

### seaborn_stylist
**Category**: Figure Generation  
**Description**: Statistical visualization  
**Skills**: seaborn, statistical_plots  
**Input**: data  
**Output**: statistical_plots

### plotly_specialist
**Category**: Figure Generation  
**Description**: Interactive visualizations  
**Skills**: plotly, interactive_viz  
**Input**: data  
**Output**: interactive_plot

### ggplot_converter
**Category**: Figure Generation  
**Description**: R ggplot2 to Python conversion  
**Skills**: plotnine, ggplot_syntax  
**Input**: r_code  
**Output**: python_plot

### publication_formatter
**Category**: Figure Generation  
**Description**: Journal-specific formatting  
**Skills**: publication_styles, journal_templates  
**Input**: figure  
**Output**: formatted_figure

### color_palette_designer
**Category**: Figure Generation  
**Description**: Accessible color scheme design  
**Skills**: colorbrewer, accessibility_checking  
**Input**: plot_type  
**Output**: color_palette

### layout_composer
**Category**: Figure Generation  
**Description**: Multi-panel figure composition  
**Skills**: matplotlib_gridspec, layout_optimization  
**Input**: figures  
**Output**: composed_figure

### annotation_specialist
**Category**: Figure Generation  
**Description**: Figure annotation and labeling  
**Skills**: annotation_tools, label_placement  
**Input**: figure  
**Output**: annotated_figure

### vector_graphics_editor
**Category**: Figure Generation  
**Description**: SVG/PDF optimization  
**Skills**: cairosvg, vector_editing  
**Input**: svg_file  
**Output**: optimized_svg

### data_viz_consultant
**Category**: Figure Generation  
**Description**: Visualization best practices  
**Skills**: viz_guidelines, chart_selection  
**Input**: data_type  
**Output**: viz_recommendations

### interactive_dashboard
**Category**: Figure Generation  
**Description**: Web-based dashboard creation  
**Skills**: dash, plotly_dash  
**Input**: data  
**Output**: dashboard_app

### animation_generator
**Category**: Figure Generation  
**Description**: Animated figure creation  
**Skills**: matplotlib_animation, ffmpeg  
**Input**: time_series_data  
**Output**: animation

### 3d_visualizer
**Category**: Figure Generation  
**Description**: 3D structure visualization  
**Skills**: py3Dmol, nglview  
**Input**: pdb_structure  
**Output**: 3d_visualization

### graph_network_visualizer
**Category**: Figure Generation  
**Description**: Network and graph visualization  
**Skills**: networkx, graphviz  
**Input**: network_data  
**Output**: network_graph

### schematic_illustrator
**Category**: Figure Generation  
**Description**: Scientific schematic creation  
**Skills**: matplotlib, illustration_tools  
**Input**: description  
**Output**: schematic

---

## Scientific Writing Agents (20)

### abstract_writer
**Category**: Scientific Writing  
**Description**: Abstract drafting and optimization  
**Skills**: text_summarization, scientific_writing  
**Input**: paper_content, target_journal  
**Output**: abstract_draft, word_count_analysis

### introduction_writer
**Category**: Scientific Writing  
**Description**: Introduction section drafting  
**Skills**: scientific_writing, literature_review  
**Input**: research_background  
**Output**: introduction

### methods_writer
**Category**: Scientific Writing  
**Description**: Methods section documentation  
**Skills**: methodology_writing, protocol_documentation  
**Input**: methods_details  
**Output**: methods_section

### results_writer
**Category**: Scientific Writing  
**Description**: Results narrative generation  
**Skills**: results_writing, statistical_reporting  
**Input**: analysis_results  
**Output**: results_section

### discussion_writer
**Category**: Scientific Writing  
**Description**: Discussion and interpretation  
**Skills**: discussion_writing, scientific_argumentation  
**Input**: results_context  
**Output**: discussion_section

### conclusion_writer
**Category**: Scientific Writing  
**Description**: Conclusion and future directions  
**Skills**: conclusion_writing, future_work_synthesis  
**Input**: study_summary  
**Output**: conclusion

### citation_manager
**Category**: Scientific Writing  
**Description**: Reference formatting and management  
**Skills**: bibtex, citation_styles  
**Input**: references  
**Output**: formatted_citations

### bibtex_converter
**Category**: Scientific Writing  
**Description**: BibTeX conversion and validation  
**Skills**: bibtex_parsing, citation_validation  
**Input**: citations  
**Output**: bibtex_file

### journal_formatter
**Category**: Scientific Writing  
**Description**: Journal-specific submission formatting  
**Skills**: journal_templates, formatting_rules  
**Input**: manuscript  
**Output**: formatted_manuscript

### cover_letter_writer
**Category**: Scientific Writing  
**Description**: Cover letter drafting  
**Skills**: letter_writing, submission_guidelines  
**Input**: manuscript_summary  
**Output**: cover_letter

### response_to_reviewers
**Category**: Scientific Writing  
**Description**: Reviewer response drafting  
**Skills**: response_writing, revision_planning  
**Input**: reviewer_comments  
**Output**: response_letter

### grant_proposal_writer
**Category**: Scientific Writing  
**Description**: Grant proposal development  
**Skills**: grant_writing, budget_planning  
**Input**: research_plan  
**Output**: grant_proposal

### specific_aims_optimizer
**Category**: Scientific Writing  
**Description**: Specific aims refinement  
**Skills**: aims_optimization, logic_modeling  
**Input**: research_objectives  
**Output**: refined_aims

### lay_summary_writer
**Category**: Scientific Writing  
**Description**: Plain language summary  
**Skills**: science_communication, plain_language  
**Input**: technical_content  
**Output**: lay_summary

### press_release_writer
**Category**: Scientific Writing  
**Description**: Media and outreach materials  
**Skills**: press_writing, media_relations  
**Input**: research_highlights  
**Output**: press_release

### thesis_writer
**Category**: Scientific Writing  
**Description**: Thesis and dissertation drafting  
**Skills**: thesis_structure, academic_writing  
**Input**: research_content  
**Output**: thesis_chapters

### presentation_writer
**Category**: Scientific Writing  
**Description**: Conference presentation materials  
**Skills**: presentation_design, slide_creation  
**Input**: research_content  
**Output**: presentation_slides

### poster_creator
**Category**: Scientific Writing  
**Description**: Scientific poster design  
**Skills**: poster_layout, visual_communication  
**Input**: research_summary  
**Output**: poster_file

### protocol_writer
**Category**: Scientific Writing  
**Description**: Standard operating procedures  
**Skills**: protocol_documentation, sop_writing  
**Input**: protocol_steps  
**Output**: sop_document

### dataset_descriptor
**Category**: Scientific Writing  
**Description**: Data availability statements  
**Skills**: data_description, repository_documentation  
**Input**: dataset_metadata  
**Output**: availability_statement
