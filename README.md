# openScience

<div align="center">

**An Open-Source AI Workbench for Scientific Research**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

*Inspired by [Claude Science](https://claude.com/product/claude-science) — An open-source agentic research environment*

[🌐 GitHub Repository](https://github.com/YakinRubaiat/openScience)

[Features](#features) • [Architecture](#architecture) • [Quick Start](#quick-start) • [Agents](#agents) • [Documentation](#documentation) • [Contributing](#contributing)

</div>

---

## Overview

**openScience** is an open-source AI workbench for scientific research that brings agentic AI capabilities to computational biology, chemistry, neuroscience, and ML research. It automates the toil between scientific questions and answers—handling database schemas, format conversions, and package interoperability—so researchers can focus on design decisions and interpretation.

### The Six Workflow Archetypes

openScience covers the core digital workflows of scientific research:

| Workflow | Description |
|----------|-------------|
| **Literature Review** | Systematic search, summarization, and synthesis of scientific literature |
| **Experiment Planning** | Protocol design, power analysis, and experimental optimization |
| **Data Management** | Organization, validation, and transformation of scientific datasets |
| **Data Analysis** | Statistical analysis, visualization, and machine learning |
| **Figure Generation** | Publication-quality figures and data visualizations |
| **Scientific Writing** | Drafting, editing, and formatting manuscripts and reports |

---

## Features

### 🧬 Domain Expertise, Ready on Day One

- **60+ Scientific Database Connectors**: PubMed, bioRxiv, AlphaFold DB, PDB, ChEMBL, GEO, SRA, and more
- **150+ Curated Skills**: BLAST, DESeq2, Seurat, Scanpy, AlphaFold2, GROMACS, RDKit, PyMOL
- **Field-Specific Templates**: Genomics, proteomics, metabolomics, drug discovery, structural biology

### 🔒 Security & Biosecurity First

- **OS-Level Sandbox**: Deny-by-default network egress with granular permission controls
- **Human-Approval Broker**: Gates code execution, network access, host file access, deletions, and MCP tools
- **Biosecurity Safeguards**: Built-in dual-use review and trajectory classification
- **Encrypted Credentials**: Local keyring storage for API keys and database credentials

### 🚀 Flexible Compute

- **Local Execution**: Run on your laptop, lab workstation, or HPC login node
- **Remote Dispatch**: Auto-detect SLURM clusters, SSH hosts, and cloud GPU instances
- **Environment Management**: Per-specialist Conda/pip environments with automatic dependency resolution
- **Persistent Sessions**: Kernels, artifacts, and state survive reboots

### 📊 Auditable Artifacts

- **Full Provenance**: Every result links to the code, data, and parameters that produced it
- **Versioned Outputs**: Track iterations of analyses, figures, and manuscripts
- **Reproducible Pipelines**: Export complete workflows as executable notebooks or scripts

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        openScience UI                           │
│                    (Browser-based Interface)                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Orchestrator                         │
│              Task routing, planning, and delegation             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Literature  │  │ Experiment  │  │    Data Management      │  │
│  │   Review    │  │  Planning   │  │       Agents            │  │
│  │  Agents     │  │   Agents    │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │    Data     │  │   Figure    │  │    Scientific Writing   │  │
│  │  Analysis   │  │ Generation  │  │       Agents            │  │
│  │   Agents    │  │   Agents    │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                        Skill Registry                           │
│           150+ tools: BLAST, DESeq2, Seurat, PyMOL...          │
├─────────────────────────────────────────────────────────────────┤
│                      Connector Framework                        │
│     60+ databases: PubMed, PDB, ChEMBL, GEO, SRA, ZINC...      │
├─────────────────────────────────────────────────────────────────┤
│                   OS-Level Sandbox                              │
│        Deny-by-default network egress, file system guards      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Compute Backend Router                      │
│    Local │ SSH Host │ SLURM Cluster │ Cloud GPU │ Serverless   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- **OS**: macOS 13+ or Linux (Ubuntu 20.04+, RHEL 8+, etc.)
- **Python**: 3.10 or higher
- **Memory**: 16GB RAM minimum (32GB recommended for large datasets)
- **Storage**: 50GB free space (more for genomics/proteomics data)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/openScience.git
cd openScience

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install openScience in development mode
pip install -e .

# Run the setup wizard
openscience init
```

### First Run

```bash
# Start the openScience daemon
openscience start

# Open the web interface
openscience ui
```

Navigate to `http://localhost:8080` in your browser.

### Your First Analysis

```python
from openscience import ScienceSession

# Initialize a session
session = ScienceSession()

# Example: Single-cell RNA-seq analysis
session.load_data("data/pbmc_10k.h5ad", format="anndata")

# The agent automatically selects appropriate tools
result = session.analyze(
    task="Quality control and clustering",
    specialist="single_cell_rnaseq"
)

# Generate publication figures
figure = session.visualize(
    result,
    type="umap",
    style="publication",
    output="figures/umap_clusters.pdf"
)

# Draft methods section
methods = session.write_methods(
    result,
    style="nature",
    citation_format="apa"
)
```

---

## Agents

openScience includes **100 specialized agents** organized into six workflow categories:

### 📚 Literature Review Agents

| Agent | Specialization |
|-------|----------------|
| `pubmed_search` | PubMed/PMC systematic literature search |
| `biorxiv_monitor` | Preprint tracking and notifications |
| `semantic_scholar` | Citation network analysis |
| `pubmed_central` | Full-text article mining |
| `clinical_trials` | Clinical trial registry search |
| `patent_search` | USPTO/EPO patent literature |
| `openalex` | Open bibliographic database |
| `lit_summarizer` | Automated literature summarization |
| `citation_graph` | Citation network visualization |
| `systematic_review` | PRISMA-compliant review automation |
| `meta_analysis` | Meta-analysis and forest plots |
| `fact_checker` | Claim verification against sources |
| `related_work_finder` | Similar research identification |
| `research_gap_analyzer` | Identification of understudied areas |
| `trend_tracker` | Emerging topic detection |

### 🧪 Experiment Planning Agents

| Agent | Specialization |
|-------|----------------|
| `power_analysis` | Statistical power calculation |
| `experimental_design` | Factorial and response surface designs |
| `sample_size_calc` | Sample size determination |
| `protocol_optimizer` | Experimental protocol optimization |
| `reagent_optimizer` | Reagent selection and concentration |
| `control_designer` | Positive/negative control selection |
| `randomization_planner` | Randomization and blinding schemes |
| `batch_effect_guardian` | Batch effect detection and correction planning |
| `dose_response_design` | Dose-response curve optimization |
| `time_course_planner` | Longitudinal study design |
| `multiplex_designer` | Multiplex assay panel design |
| `feasibility_checker` | Resource and timeline feasibility |
| `cost_estimator` | Budget and cost projection |
| `risk_assessor` | Technical risk identification |
| `preregistration_writer` | Preregistration document drafting |

### 💾 Data Management Agents

| Agent | Specialization |
|-------|----------------|
| `data_ingestor` | Multi-format data import |
| `format_converter` | File format conversion |
| `metadata_extractor` | Metadata extraction and validation |
| `data_validator` | Quality and integrity checking |
| `data_cleaner` | Outlier detection and cleaning |
| `normalization_expert` | Normalization method selection |
| `batch_corrector` | Batch effect correction |
| `data_integrator` | Multi-omics data integration |
| `database_writer` | Database ingestion |
| `s3_manager` | Cloud storage management |
| `version_controller` | Data versioning and lineage |
| `privacy_guardian` | PHI/PII detection and masking |
| `compression_optimizer` | Storage optimization |
| `backup_manager` | Backup and archival |
| `provenance_tracker` | Complete data lineage tracking |

### 📈 Data Analysis Agents

| Agent | Specialization |
|-------|----------------|
| `qc_analyzer` | Quality control metrics |
| `deseq2_specialist` | Bulk RNA-seq differential expression |
| `scanpy_specialist` | Single-cell analysis (Scanpy) |
| `seurat_specialist` | Single-cell analysis (Seurat) |
| `cellranger_specialist` | 10x Genomics preprocessing |
| `gsea_analyzer` | Gene set enrichment analysis |
| `pathway_analyzer` | Pathway and network analysis |
| `variant_caller` | Variant detection and annotation |
| `chip_seq_analyzer` | ChIP-seq peak calling and analysis |
| `atac_seq_analyzer` | ATAC-seq analysis |
| `methylation_analyzer` | DNA methylation analysis |
| `metagenomics_analyzer` | Microbiome analysis |
| `proteomics_analyzer` | Mass spec proteomics |
| `metabolomics_analyzer` | Metabolomics data analysis |
| `image_analyzer` | Bioimage analysis (CellProfiler, Fiji) |
| `flow_cytometry_analyzer` | Flow cytometry gating and analysis |
| `ml_modeler` | Machine learning model development |
| `deep_learning_specialist` | Neural network design and training |
| `statistical_modeler` | Statistical inference and modeling |
| `survival_analyzer` | Survival analysis and Kaplan-Meier |

### 📊 Figure Generation Agents

| Agent | Specialization |
|-------|----------------|
| `matplotlib_stylist` | Matplotlib figure optimization |
| `seaborn_stylist` | Statistical visualization |
| `plotly_specialist` | Interactive visualizations |
| `ggplot_converter` | R ggplot2 to Python conversion |
| `publication_formatter` | Journal-specific formatting |
| `color_palette_designer` | Accessible color scheme design |
| `layout_composer` | Multi-panel figure composition |
| `annotation_specialist` | Figure annotation and labeling |
| `vector_graphics_editor` | SVG/PDF optimization |
| `data_viz_consultant` | Visualization best practices |
| `interactive_dashboard` | Web-based dashboard creation |
| `animation_generator` | Animated figure creation |
| `3d_visualizer` | 3D structure visualization |
| `graph_network_visualizer` | Network and graph visualization |
| `schematic_illustrator` | Scientific schematic creation |

### ✍️ Scientific Writing Agents

| Agent | Specialization |
|-------|----------------|
| `abstract_writer` | Abstract drafting and optimization |
| `introduction_writer` | Introduction section drafting |
| `methods_writer` | Methods section documentation |
| `results_writer` | Results narrative generation |
| `discussion_writer` | Discussion and interpretation |
| `conclusion_writer` | Conclusion and future directions |
| `citation_manager` | Reference formatting and management |
| `bibtex_converter` | BibTeX conversion and validation |
| `journal_formatter` | Journal-specific submission formatting |
| `cover_letter_writer` | Cover letter drafting |
| `response_to_reviewers` | Reviewer response drafting |
| `grant_proposal_writer` | Grant proposal development |
| `specific_aims_optimizer` | Specific aims refinement |
| `lay_summary_writer` | Plain language summary |
| `press_release_writer` | Media and outreach materials |

---

## Configuration

### Settings

Access settings via `openscience config` or the web interface:

```yaml
# ~/.openscience/config.yaml

# Compute backends
compute:
  default: local
  backends:
    - name: gpu-cluster
      type: slurm
      host: cluster.institution.edu
      partition: gpu
      gpus_per_node: 4
    
    - name: cloud-gpu
      type: aws
      instance_type: p3.2xlarge
      
# Database credentials (encrypted)
credentials:
  pubmed_api_key: ${PUBMED_API_KEY}
  chembl_api_key: ${CHEMBL_API_KEY}
  
# Security settings
security:
  network_policy: deny_all
  allowed_domains:
    - pubmed.ncbi.nlm.nih.gov
    - ebi.ac.uk
    - rcsb.org
    
# Specialist configuration
specialists:
  single_cell_rnaseq:
    conda_env: scanpy_env
    default_tools:
      - scanpy
      - scrublet
      - cellrank
      
# Review criteria
reviewer:
  criteria:
    - statistical_rigor
    - code_quality
    - documentation_completeness
```

### Environment Variables

```bash
# Required
export OPENSCIENCE_HOME="~/.openscience"
export OPENSCIENCE_DATA="/path/to/data"

# API Keys (use secret management in production)
export PUBMED_API_KEY="your_key"
export CHEMBL_API_KEY="your_key"
export AWS_ACCESS_KEY_ID="your_key"

# Optional
export OPENSCIENCE_LOG_LEVEL="INFO"
export OPENSCIENCE_CACHE_SIZE="10GB"
```

---

## Development

### Project Structure

```
openScience/
├── src/
│   └── openscience/
│       ├── __init__.py
│       ├── core/                 # Core orchestration
│       │   ├── session.py
│       │   ├── orchestrator.py
│       │   └── sandbox.py
│       ├── agents/               # 100 specialized agents
│       │   ├── literature/       # 15 agents
│       │   ├── experiment/       # 15 agents
│       │   ├── data_management/  # 15 agents
│       │   ├── analysis/         # 20 agents
│       │   ├── visualization/    # 15 agents
│       │   └── writing/          # 20 agents
│       ├── connectors/           # 60+ database connectors
│       ├── skills/               # 150+ scientific tools
│       ├── compute/              # Compute backends
│       └── security/             # Sandbox and policies
├── tests/
├── docs/
├── examples/
├── pyproject.toml
└── README.md
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=openscience --cov-report=html

# Run specific test category
pytest tests/agents/
pytest tests/connectors/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/

# Type checking
mypy src/
```

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Adding a New Agent

```python
# src/openscience/agents/analysis/my_agent.py

from openscience.core.agent import BaseAgent, AgentMetadata

class MyAnalysisAgent(BaseAgent):
    """Custom analysis agent for [specific domain]."""
    
    metadata = AgentMetadata(
        name="my_analysis",
        category="analysis",
        description="Description of analysis capability",
        required_skills=["tool1", "tool2"],
        input_types=["anndata", "csv"],
        output_types=["figure", "table"]
    )
    
    async def execute(self, task, context):
        # Agent implementation
        result = await self.run_skill("tool1", context.data)
        return self.format_result(result)
```

### Adding a New Connector

```python
# src/openscience/connectors/my_database.py

from openscience.core.connector import BaseConnector, ConnectorMetadata

class MyDatabaseConnector(BaseConnector):
    """Connector for MyDatabase API."""
    
    metadata = ConnectorMetadata(
        name="my_database",
        base_url="https://api.mydatabase.org",
        auth_type="api_key",
        rate_limit=100  # requests per minute
    )
    
    async def search(self, query: str, **kwargs):
        # Implementation
        pass
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Inspired by [Claude Science](https://claude.ai/product/science) from Anthropic
- Built on the shoulders of giants: NumPy, SciPy, pandas, scikit-learn, Biopython, Scanpy, Seurat, and countless other open-source scientific tools
- The scientific Python community for decades of foundational work

---

## Citation

If you use openScience in your research, please cite:

```bibtex
@software{openscience2025,
  title = {openScience: An Open-Source AI Workbench for Scientific Research},
  author = {openScience Contributors},
  year = {2025},
  url = {https://github.com/yourusername/openScience},
  version = {0.1.0}
}
```

---

<div align="center">

**[Get Started](docs/getting-started.md)** • **[Documentation](docs/)** • **[Agent Catalog](docs/agents.md)** • **[API Reference](docs/api.md)**

🧬 **openScience** — Accelerating scientific discovery through open, agentic AI 🧬

</div>
