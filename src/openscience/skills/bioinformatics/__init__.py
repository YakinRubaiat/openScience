"""Bioinformatics skill implementations backed by scanpy/anndata.

This module provides the first *real* skill backend for openScience.
It implements single-cell RNA-seq loading, QC, clustering, and figure
generation using the standard scientific Python stack:

- ``scanpy`` / ``anndata`` for single-cell analysis
- ``pandas`` / ``numpy`` for data handling
- ``matplotlib`` for publication-quality figures

The skill class is deliberately stateless across operations: an
:class:`anndata.AnnData` object is passed (by reference) through the
``context`` dict so each operation can mutate/read it, mirroring how
agents actually chain together in a pipeline.
"""

from openscience.skills.bioinformatics.skill import BioinformaticsSkill

__all__ = ["BioinformaticsSkill"]
