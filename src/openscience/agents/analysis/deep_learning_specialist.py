"""Neural network design and training agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class DeepLearningSpecialistAgent(BaseAgent):
    """Agent for neural network design and training."""

    metadata = AgentMetadata(
        name="deep_learning_specialist",
        category="analysis",
        description="Neural network design and training",
        required_skills=["pytorch", "tensorflow"],
        input_types=["training_data"],
        output_types=["model_weights"],
    )

    async def execute(self, task, context):
        """Run neural network design and training."""
        result = await self.run_skill(
            "pytorch",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
