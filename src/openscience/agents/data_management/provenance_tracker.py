"""Complete data lineage tracking agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ProvenanceTrackerAgent(BaseAgent):
    """Agent for complete data lineage tracking."""

    metadata = AgentMetadata(
        name="provenance_tracker",
        category="data_management",
        description="Complete data lineage tracking",
        required_skills=["provenance_modeling", "workflow_tracking"],
        input_types=["pipeline_steps"],
        output_types=["provenance_graph"],
    )

    async def execute(self, task, context):
        """Run complete data lineage tracking."""
        result = await self.run_skill(
            "provenance_modeling",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
