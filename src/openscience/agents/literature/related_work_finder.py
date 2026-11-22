"""Similar research identification agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class RelatedWorkFinderAgent(BaseAgent):
    """Agent for similar research identification."""

    metadata = AgentMetadata(
        name="related_work_finder",
        category="literature",
        description="Similar research identification",
        required_skills=["semantic_similarity", "paper_clustering"],
        input_types=["target_paper"],
        output_types=["similar_papers"],
    )

    async def execute(self, task, context):
        """Run similar research identification."""
        result = await self.run_skill(
            "semantic_similarity",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
