"""Real working orchestrator subclass that binds the RDKit skill.

Demonstrates the deployment pattern documented in `AgentOrchestrator.execute_skill`:
'Deployments can subclass AgentOrchestrator to bind real tool implementations.'
"""

from __future__ import annotations

from typing import Any

from openscience.core.orchestrator import AgentOrchestrator
from openscience.skills.cheminformatics import rdkit_skill


class RDKitOrchestrator(AgentOrchestrator):
    """Orchestrator with a real cheminformatics skill bound."""

    def execute_skill(self, skill_name: str, operation: str, **kwargs) -> Any:
        if skill_name == "rdkit":
            return rdkit_skill.run(operation, **kwargs)
        return super().execute_skill(skill_name, operation, **kwargs)
