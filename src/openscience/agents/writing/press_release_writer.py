"""Media and outreach materials agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class PressReleaseWriterAgent(BaseAgent):
    """Agent for media and outreach materials."""

    metadata = AgentMetadata(
        name="press_release_writer",
        category="writing",
        description="Media and outreach materials",
        required_skills=["press_writing", "media_relations"],
        input_types=["research_highlights"],
        output_types=["press_release"],
    )

    async def execute(self, task, context):
        """Run media and outreach materials."""
        result = await self.run_skill(
            "press_writing",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
