"""Reviewer response drafting agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ResponseToReviewersAgent(BaseAgent):
    """Agent for reviewer response drafting."""

    metadata = AgentMetadata(
        name="response_to_reviewers",
        category="writing",
        description="Reviewer response drafting",
        required_skills=["response_writing", "revision_planning"],
        input_types=["reviewer_comments"],
        output_types=["response_letter"],
    )

    async def execute(self, task, context):
        """Run reviewer response drafting."""
        result = await self.run_skill(
            "response_writing",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
