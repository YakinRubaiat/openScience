#!/usr/bin/env python3
"""
Setup script for openScience package.

This builds the complete Python library for openScience with all components:
core framework, 111 agents, API, UI, and Docker infrastructure.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = [
        line.strip()
        for line in requirements_path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

# Read development requirements
dev_requirements_path = Path(__file__).parent / "requirements-dev.txt"
dev_requirements = []
if dev_requirements_path.exists():
    dev_requirements = [
        line.strip()
        for line in dev_requirements_path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="openscience",
    version="0.1.0",
    author="openScience Contributors",
    author_email="contributors@openscience.dev",
    description="An Open-Source AI Workbench for Scientific Research",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/YakinRubaiat/openScience",
    project_urls={
        "Documentation": "https://yakinrubaiat.github.io/openScience/",
        "Source": "https://github.com/YakinRubaiat/openScience",
        "Tracker": "https://github.com/YakinRubaiat/openScience/issues",
        "Docker Hub": "https://hub.docker.com/r/openscience/openscience",
    },
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords=(
        "openscience, science, research, ai, agent, llm, bioinformatics, "
        "cheminformatics, genomics, proteomics, machine-learning, "
        "scientific-computing, workflow-automation"
    ),
    # Package discovery
    package_dir={"": "src"},
    packages=find_packages(where="src", exclude=["tests*", "docs*", "examples*"]),
    include_package_data=True,
    package_data={
        "openscience": [
            "py.typed",
            "agents/*/**/*.py",
            "api/**/*.py",
            "core/*.py",
            "connectors/**/*.py",
            "skills/**/*.py",
            "workers/*.py",
        ],
    },
    # Dependencies
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        # Optional API dependencies
        "api": [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "sqlalchemy>=2.0.0",
            "alembic>=1.12.0",
            "pydantic>=2.4.0",
            "pydantic-settings>=2.0.0",
            "python-jose[cryptography]>=3.3.0",
            "passlib[bcrypt]>=1.7.4",
            "python-multipart>=0.0.6",
        ],
        # Optional UI dependencies
        "ui": [
            "flask>=2.3.0",
            "flask-cors>=4.0.0",
            "flask-socketio>=5.3.0",
        ],
        # Optional worker dependencies
        "worker": [
            "celery>=5.3.0",
            "redis>=5.0.0",
            "kombu>=5.3.0",
        ],
        # Bio/scientific dependencies
        "bio": [
            "biopython>=1.81",
            "scanpy>=1.9.0",
            "anndata>=0.9.0",
            "pysam>=0.21.0",
            "numpy>=1.24.0",
            "pandas>=2.0.0",
            "scipy>=1.10.0",
            "scikit-learn>=1.3.0",
            "matplotlib>=3.7.0",
            "seaborn>=0.12.0",
            "plotly>=5.14.0",
        ],
        # Chemistry dependencies
        "chem": [
            "rdkit>=2023.3.1",
            "openmm>=8.0.0",
            "parmed>=4.0.0",
        ],
        # ML dependencies
        "ml": [
            "torch>=2.0.0",
            "tensorflow>=2.13.0",
            "xgboost>=1.7.0",
            "transformers>=4.30.0",
        ],
        # Visualization dependencies
        "viz": [
            "dash>=2.10.0",
            "bokeh>=3.1.0",
            "altair>=5.0.0",
            "py3dmol>=1.8.0",
            "nglview>=3.0.0",
        ],
        # Development dependencies
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.5.0",
            "pre-commit>=3.3.0",
        ],
        # Documentation dependencies
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.4.0",
            "mkdocstrings[python]>=0.23.0",
        ],
        # All dependencies
        "all": [
            "openscience[api,ui,worker,bio,chem,ml,viz,dev,docs]",
        ],
    },
    # CLI entry points
    entry_points={
        "console_scripts": [
            "openscience=openscience.cli:cli",
        ],
    },
    # Type information
    zip_safe=False,
    zip_check=False,
)
