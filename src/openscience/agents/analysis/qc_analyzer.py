"""Quality control metrics agent for data analysis."""

from openscience.core.agent import BaseAgent, AgentMetadata


class QCAnalyzerAgent(BaseAgent):
    """Agent for comprehensive quality control analysis."""

    metadata = AgentMetadata(
        name="qc_analyzer",
        category="analysis",
        description="Quality control metrics",
        required_skills=["scanpy", "seurat", "multiqc"],
        input_types=["anndata", "seurat_object", "fastq"],
        output_types=["qc_report", "qc_plots", "filtered_data"],
    )

    async def execute(self, task, context):
        """Run comprehensive QC analysis."""
        data = context.data
        data_type = task.parameters.get("data_type", "auto")

        if data_type == "auto":
            data_type = self.detect_data_type(data)

        qc_results = await self.run_skill(
            "scanpy" if data_type == "single_cell" else "multiqc",
            operation="qc_analysis",
            data=data,
        )

        return self.format_result(qc_results)
