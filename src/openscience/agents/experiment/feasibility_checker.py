"""Resource and timeline feasibility agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class FeasibilityCheckerAgent(BaseAgent):
    """Agent for resource and timeline feasibility."""

    metadata = AgentMetadata(
        name="feasibility_checker",
        category="experiment",
        description="Resource and timeline feasibility",
        required_skills=["resource_planning", "timeline_estimation"],
        input_types=["project_scope"],
        output_types=["feasibility_report"],
    )

    async def execute(self, task, context):
        """Run resource and timeline feasibility."""
        result = await self.run_skill(
            "resource_planning",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
