"""Animated figure creation agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class AnimationGeneratorAgent(BaseAgent):
    """Agent for animated figure creation."""

    metadata = AgentMetadata(
        name="animation_generator",
        category="visualization",
        description="Animated figure creation",
        required_skills=["matplotlib_animation", "ffmpeg"],
        input_types=["time_series_data"],
        output_types=["animation"],
    )

    async def execute(self, task, context):
        """Run animated figure creation."""
        result = await self.run_skill(
            "matplotlib_animation",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
