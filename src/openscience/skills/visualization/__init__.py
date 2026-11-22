"""Visualization skills for openScience.

Each module implements one skill (a named tool that agents call via
``AgentOrchestrator.execute_skill``). All skills operate on plain Python /
numpy / pandas data structures and matplotlib figures.
"""

from . import colorbrewer, matplotlib_gridspec, matplotlib_skill, seaborn_skill

__all__ = [
    "colorbrewer",
    "matplotlib_gridspec",
    "matplotlib_skill",
    "seaborn_skill",
]
