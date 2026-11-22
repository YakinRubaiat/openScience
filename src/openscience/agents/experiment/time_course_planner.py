"""Longitudinal study design agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class TimeCoursePlannerAgent(BaseAgent):
    """Agent for longitudinal study design."""

    metadata = AgentMetadata(
        name="time_course_planner",
        category="experiment",
        description="Longitudinal study design",
        required_skills=["time_series_design", "longitudinal_analysis"],
        input_types=["study_duration"],
        output_types=["time_points"],
    )

    async def execute(self, task, context):
        """Run longitudinal study design."""
        result = await self.run_skill(
            "time_series_design",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
