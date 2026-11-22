"""Code Quality Review Agent for openScience."""

from openscience.core.agent import AgentMetadata, BaseAgent


class CodeQualityReviewerAgent(BaseAgent):
    """
    Agent for reviewing code quality, style, and maintainability.

    Reviews code for:
    - PEP 8 compliance
    - Code complexity (cyclomatic complexity)
    - Code duplication
    - Naming conventions
    - Documentation coverage
    - Type hint coverage
    - Test coverage
    """

    metadata = AgentMetadata(
        name="code_quality_reviewer",
        category="review",
        description="Reviews code quality, style, and maintainability",
        required_skills=["pylint", "radon", "black", "mypy"],
        input_types=["source_code"],
        output_types=["quality_report", "complexity_metrics", "recommendations"],
    )

    async def execute(self, task, context):
        """Execute code quality review."""
        target_path = task.parameters.get("target_path", "src/")

        # Run code quality checks
        pylint_results = await self.run_skill(
            "pylint",
            operation="scan",
            path=target_path,
        )

        complexity_results = await self.run_skill(
            "radon",
            operation="complexity",
            path=target_path,
        )

        formatting_check = await self.run_skill(
            "black",
            operation="check",
            path=target_path,
        )

        type_check = await self.run_skill(
            "mypy",
            operation="check",
            path=target_path,
        )

        # Analyze code duplication
        duplication_results = await self.run_skill(
            "pylint",
            operation="duplication",
            path=target_path,
        )

        return self.format_result(
            {
                "pylint_score": pylint_results.get("score", 0),
                "complexity_metrics": complexity_results,
                "formatting_issues": formatting_check.get("issues", []),
                "type_errors": type_check.get("errors", []),
                "duplication": duplication_results,
                "recommendations": self._generate_recommendations(
                    pylint_results,
                    complexity_results,
                    formatting_check,
                    type_check,
                ),
            }
        )

    def _generate_recommendations(self, pylint, complexity, formatting, typing):
        """Generate code quality recommendations."""
        recommendations = []

        if pylint.get("score", 10) < 8.0:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "code_quality",
                    "action": "Improve pylint score to 8.0+",
                    "current_score": pylint.get("score"),
                }
            )

        high_complexity = [f for f in complexity if f.get("complexity", 0) > 10]
        if high_complexity:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "complexity",
                    "action": f"Refactor {len(high_complexity)} complex functions",
                    "functions": [f["name"] for f in high_complexity[:5]],
                }
            )

        if typing.get("error_count", 0) > 0:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "typing",
                    "action": f"Fix {typing['error_count']} type errors",
                }
            )

        return recommendations
