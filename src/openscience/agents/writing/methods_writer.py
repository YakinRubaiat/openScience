"""Methods section writing agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class MethodsWriterAgent(BaseAgent):
    """Agent for drafting methods sections from analysis results."""

    metadata = AgentMetadata(
        name="methods_writer",
        category="writing",
        description="Methods section writing",
        required_skills=["scientific_writing"],
        input_types=["analysis_result", "journal_style"],
        output_types=["methods_text"],
    )

    async def execute(self, task, context):
        """Generate a methods section from analysis results."""
        result = task.parameters.get("analysis_result")
        journal = task.parameters.get("journal_style", "nature")
        citation_format = task.parameters.get("citation_format", "apa")

        text = await self.run_skill(
            "scientific_writing",
            operation="write_methods",
            result=result,
            journal=journal,
            citation_format=citation_format,
        )

        return self.format_result({"methods_text": text, "journal_style": journal})
