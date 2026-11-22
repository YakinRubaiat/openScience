"""Figure annotation and labeling agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class AnnotationSpecialistAgent(BaseAgent):
    """Agent for figure annotation and labeling."""

    metadata = AgentMetadata(
        name="annotation_specialist",
        category="visualization",
        description="Figure annotation and labeling",
        required_skills=["annotation_tools", "label_placement"],
        input_types=["figure"],
        output_types=["annotated_figure"],
    )

    async def execute(self, task, context):
        """Run figure annotation and labeling."""
        result = await self.run_skill(
            "annotation_tools",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
