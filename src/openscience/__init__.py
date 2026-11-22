"""openScience: An Open-Source AI Workbench for Scientific Research.

A complete, production-ready Python library for agentic scientific research
with 111 specialized agents, Docker infrastructure, REST API, and comprehensive
testing framework.
"""

__version__ = "0.1.0"
__author__ = "openScience Contributors"
__email__ = "contributors@openscience.dev"
__license__ = "MIT"
__copyright__ = "Copyright 2026 openScience Contributors"

# Core framework imports
from openscience.core.session import ScienceSession
from openscience.core.orchestrator import AgentOrchestrator
from openscience.core.agent import BaseAgent, AgentMetadata
from openscience.core.sandbox import Sandbox, SecurityPolicy, SecurityError

# API imports (optional, requires fastapi)
try:
    from openscience.api.main import app as api_app
    _HAS_API = True
except ImportError:
    _HAS_API = False

# Agent imports (optional, auto-discovered)
try:
    from openscience.agents import *
    _HAS_AGENTS = True
except ImportError:
    _HAS_AGENTS = False

__all__ = [
    # Core
    "ScienceSession",
    "AgentOrchestrator",
    "BaseAgent",
    "AgentMetadata",
    "Sandbox",
    "SecurityPolicy",
    "SecurityError",
    # Version info
    "__version__",
    "__author__",
    "__license__",
]

# Conditional exports
if _HAS_API:
    __all__.append("api_app")
    
if _HAS_AGENTS:
    # Auto-import all agents
    from openscience.core.orchestrator import AgentOrchestrator
    _temp_orch = AgentOrchestrator()
    __all__.extend(_temp_orch.agents.keys())
    del _temp_orch
