"""BibTeX conversion and validation agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class BibtexConverterAgent(BaseAgent):
    """Agent for bibTeX conversion and validation."""

    metadata = AgentMetadata(
        name="bibtex_converter",
        category="writing",
        description="BibTeX conversion and validation",
        required_skills=["bibtex_parsing", "citation_validation"],
        input_types=["citations"],
        output_types=["bibtex_file"],
    )

    async def execute(self, task, context):
        """Run bibTeX conversion and validation."""
        result = await self.run_skill(
            "bibtex_parsing",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
