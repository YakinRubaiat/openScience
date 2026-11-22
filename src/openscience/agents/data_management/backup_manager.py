"""Backup and archival agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class BackupManagerAgent(BaseAgent):
    """Agent for backup and archival."""

    metadata = AgentMetadata(
        name="backup_manager",
        category="data_management",
        description="Backup and archival",
        required_skills=["backup_strategies", "archival_systems"],
        input_types=["data"],
        output_types=["backup_locations"],
    )

    async def execute(self, task, context):
        """Run backup and archival."""
        result = await self.run_skill(
            "backup_strategies",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
