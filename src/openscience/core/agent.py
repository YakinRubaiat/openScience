"""Base agent class for all specialized agents."""

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AgentMetadata:
    """Metadata describing an agent's capabilities."""

    name: str
    category: str
    description: str
    required_skills: list[str] = field(default_factory=list)
    input_types: list[str] = field(default_factory=list)
    output_types: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    """
    Abstract base class for all openScience agents.

    Each of the 100 specialized agents extends this class to provide
    domain-specific capabilities while maintaining a consistent interface.
    """

    metadata: AgentMetadata

    def __init__(self, orchestrator: Optional[Any] = None):
        """
        Initialize the agent.

        Args:
            orchestrator: Reference to the parent orchestrator
        """
        self.orchestrator = orchestrator
        self._skills: dict[str, Any] = {}

    @abstractmethod
    async def execute(self, task, context) -> Any:
        """
        Execute the agent's primary function.

        Args:
            task: Task object with description and parameters
            context: Execution context with data and state

        Returns:
            Result of the agent's operation
        """

    async def run_skill(self, skill_name: str, operation: str, **kwargs) -> Any:
        """
        Execute a skill (tool) required by this agent.

        Args:
            skill_name: Name of the skill to execute
            operation: Operation to perform
            **kwargs: Operation-specific arguments

        Returns:
            Skill execution result
        """
        if self.orchestrator is None:
            raise RuntimeError("Agent not connected to orchestrator")

        result = self.orchestrator.execute_skill(
            skill_name=skill_name,
            operation=operation,
            **kwargs,
        )
        if inspect.isawaitable(result):
            result = await result
        return result

    def format_result(self, data: Any, **metadata) -> Any:
        """
        Format the agent's result.

        Args:
            data: Result data
            **metadata: Additional metadata

        Returns:
            Formatted result object
        """
        return {
            "agent": self.metadata.name,
            "data": data,
            "metadata": metadata,
        }
