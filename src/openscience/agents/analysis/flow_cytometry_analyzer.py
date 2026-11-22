"""Flow cytometry gating and analysis agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class FlowCytometryAnalyzerAgent(BaseAgent):
    """Agent for flow cytometry gating and analysis."""

    metadata = AgentMetadata(
        name="flow_cytometry_analyzer",
        category="analysis",
        description="Flow cytometry gating and analysis",
        required_skills=["flowcore", "flowjo"],
        input_types=["fcs_files"],
        output_types=["gating_results"],
    )

    async def execute(self, task, context):
        """Run flow cytometry gating and analysis."""
        result = await self.run_skill(
            "flowcore",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
