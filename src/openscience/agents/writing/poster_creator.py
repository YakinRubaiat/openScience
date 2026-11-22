"""Scientific poster design agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class PosterCreatorAgent(BaseAgent):
    """Agent for scientific poster design."""

    metadata = AgentMetadata(
        name="poster_creator",
        category="writing",
        description="Scientific poster design",
        required_skills=["poster_layout", "visual_communication"],
        input_types=["research_summary"],
        output_types=["poster_file"],
    )

    async def execute(self, task, context):
        """Run scientific poster design."""
        result = await self.run_skill(
            "poster_layout",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
