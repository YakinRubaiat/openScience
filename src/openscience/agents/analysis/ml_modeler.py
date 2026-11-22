"""Machine learning model development agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class MlModelerAgent(BaseAgent):
    """Agent for machine learning model development."""

    metadata = AgentMetadata(
        name="ml_modeler",
        category="analysis",
        description="Machine learning model development",
        required_skills=["scikit-learn", "model_training"],
        input_types=["features"],
        output_types=["trained_model"],
    )

    async def execute(self, task, context):
        """Run machine learning model development."""
        result = await self.run_skill(
            "scikit-learn",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
