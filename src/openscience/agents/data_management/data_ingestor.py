"""Multi-format data import agent."""

from pathlib import Path
from typing import Optional

from openscience.core.agent import BaseAgent, AgentMetadata


# Map common file extensions to canonical load format names.
_EXTENSION_FORMAT_MAP = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".txt": "tsv",
    ".tab": "tsv",
    ".xlsx": "excel",
    ".xls": "excel",
    ".parquet": "parquet",
    ".pq": "parquet",
    ".json": "json",
    ".jsonl": "jsonl",
    ".ndjson": "jsonl",
    ".pkl": "pickle",
    ".pickle": "pickle",
    ".h5": "hdf5",
    ".hdf5": "hdf5",
    ".h5ad": "h5ad",
    ".loom": "loom",
    ".zarr": "zarr",
    ".mtx": "mtx",
    ".feather": "feather",
    ".arrow": "arrow",
    ".sav": "spss",
    ".dta": "stata",
    ".nc": "netcdf",
    ".fasta": "fasta",
    ".fa": "fasta",
    ".fastq": "fastq",
    ".fq": "fastq",
    ".vcf": "vcf",
    ".bam": "bam",
    ".sam": "sam",
    ".bed": "bed",
    ".gff": "gff",
    ".gtf": "gtf",
}


class DataIngestorAgent(BaseAgent):
    """Agent for importing data from various file formats."""

    metadata = AgentMetadata(
        name="data_ingestor",
        category="data_management",
        description="Multi-format data import",
        required_skills=["pandas", "anndata", "bioio"],
        input_types=["file_path", "format_hint"],
        output_types=["dataframe", "anndata", "metadata"],
    )

    async def execute(self, task, context):
        """Import data from file."""
        file_path = task.parameters.get("file_path")
        format_hint = task.parameters.get("format_hint", "auto")

        if format_hint == "auto":
            format_hint = self.detect_format(file_path)

        data = await self.run_skill(
            "bioio",
            operation="load",
            file_path=file_path,
            format=format_hint,
        )

        return self.format_result({"data": data, "format": format_hint})

    @staticmethod
    def detect_format(file_path: Optional[str]) -> str:
        """Detect the data format from a file path's extension.

        Args:
            file_path: Path-like value to the target file, or ``None``.

        Returns:
            Detected format name (e.g. ``"csv"``, ``"h5ad"``). Falls back to
            ``"csv"`` for unknown or missing extensions, which is the
            safest default for tabular scientific data.
        """
        if not file_path:
            return "csv"

        suffix = Path(str(file_path)).suffix.lower()
        if not suffix:
            return "csv"

        return _EXTENSION_FORMAT_MAP.get(suffix, "csv")
