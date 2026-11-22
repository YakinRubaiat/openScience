"""Discussion and interpretation agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class DiscussionWriterAgent(BaseAgent):
    """Agent for discussion and interpretation."""

    metadata = AgentMetadata(
        name="discussion_writer",
        category="writing",
        description="Discussion and interpretation",
        required_skills=["discussion_writing", "scientific_argumentation"],
        input_types=["results_context"],
        output_types=["discussion_section"],
    )

    async def execute(self, task, context):
        """Run discussion and interpretation."""
        result = await self.run_skill(
            "discussion_writing",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
