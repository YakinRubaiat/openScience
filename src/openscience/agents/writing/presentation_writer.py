"""Conference presentation materials agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class PresentationWriterAgent(BaseAgent):
    """Agent for conference presentation materials."""

    metadata = AgentMetadata(
        name="presentation_writer",
        category="writing",
        description="Conference presentation materials",
        required_skills=["presentation_design", "slide_creation"],
        input_types=["research_content"],
        output_types=["presentation_slides"],
    )

    async def execute(self, task, context):
        """Run conference presentation materials."""
        result = await self.run_skill(
            "presentation_design",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
