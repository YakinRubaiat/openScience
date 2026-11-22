"""Thesis and dissertation drafting agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ThesisWriterAgent(BaseAgent):
    """Agent for thesis and dissertation drafting."""

    metadata = AgentMetadata(
        name="thesis_writer",
        category="writing",
        description="Thesis and dissertation drafting",
        required_skills=["thesis_structure", "academic_writing"],
        input_types=["research_content"],
        output_types=["thesis_chapters"],
    )

    async def execute(self, task, context):
        """Run thesis and dissertation drafting."""
        result = await self.run_skill(
            "thesis_structure",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
