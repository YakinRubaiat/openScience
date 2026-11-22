"""Database ingestion agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class DatabaseWriterAgent(BaseAgent):
    """Agent for database ingestion."""

    metadata = AgentMetadata(
        name="database_writer",
        category="data_management",
        description="Database ingestion",
        required_skills=["database_connectors", "schema_management"],
        input_types=["data"],
        output_types=["database_records"],
    )

    async def execute(self, task, context):
        """Run database ingestion."""
        result = await self.run_skill(
            "database_connectors",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
