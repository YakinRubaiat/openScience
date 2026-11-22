"""Reference formatting and management agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class CitationManagerAgent(BaseAgent):
    """Agent for reference formatting and management."""

    metadata = AgentMetadata(
        name="citation_manager",
        category="writing",
        description="Reference formatting and management",
        required_skills=["bibtex", "citation_styles"],
        input_types=["references"],
        output_types=["formatted_citations"],
    )

    async def execute(self, task, context):
        """Run reference formatting and management."""
        result = await self.run_skill(
            "bibtex",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
