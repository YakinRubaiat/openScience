"""Introduction section drafting agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class IntroductionWriterAgent(BaseAgent):
    """Agent for introduction section drafting."""

    metadata = AgentMetadata(
        name="introduction_writer",
        category="writing",
        description="Introduction section drafting",
        required_skills=["scientific_writing", "literature_review"],
        input_types=["research_background"],
        output_types=["introduction"],
    )

    async def execute(self, task, context):
        """Run introduction section drafting."""
        result = await self.run_skill(
            "scientific_writing",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
