"""Orchestrator extension that binds real skill implementations.

The default AgentOrchestrator.execute_skill() is a stub. This subclass
routes skill calls to real implementations in openscience.skills.general.
"""

from typing import Any, Optional

from openscience.core.agent import BaseAgent
from openscience.core.orchestrator import AgentOrchestrator
from openscience.skills import general as general_skills


class RealSkillOrchestrator(AgentOrchestrator):
    """Orchestrator that executes real skills instead of stubs."""

    def __init__(
        self,
        sandbox: Optional[Any] = None,
        compute_backend: str = "local",
        agent_registry: Optional[dict[str, type[BaseAgent]]] = None,
        skill_registry: Optional[dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(
            sandbox=sandbox,
            compute_backend=compute_backend,
            agent_registry=agent_registry,
            **kwargs,
        )
        self.skill_registry = skill_registry or general_skills.SKILL_REGISTRY

    def execute_skill(self, skill_name: str, operation: str, **kwargs) -> Any:
        if skill_name not in self.skill_registry:
            raise ValueError(f"Unknown skill: {skill_name}")
        module = self.skill_registry[skill_name]
        return module.run(operation=operation, **kwargs)
