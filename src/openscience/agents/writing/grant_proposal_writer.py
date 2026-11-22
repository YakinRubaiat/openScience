"""Grant proposal development agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class GrantProposalWriterAgent(BaseAgent):
    """Agent for grant proposal development."""

    metadata = AgentMetadata(
        name="grant_proposal_writer",
        category="writing",
        description="Grant proposal development",
        required_skills=["grant_writing", "budget_planning"],
        input_types=["research_plan"],
        output_types=["grant_proposal"],
    )

    async def execute(self, task, context):
        """Run grant proposal development."""
        result = await self.run_skill(
            "grant_writing",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
