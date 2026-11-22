"""openScience: An Open-Source AI Workbench for Scientific Research."""

__version__ = "0.1.0"
__author__ = "openScience Contributors"

from openscience.core.session import ScienceSession
from openscience.core.orchestrator import AgentOrchestrator

__all__ = [
    "ScienceSession",
    "AgentOrchestrator",
    "__version__",
]
