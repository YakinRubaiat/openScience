"""Dependency Review Agent for openScience."""

from openscience.core.agent import AgentMetadata, BaseAgent


class DependencyReviewerAgent(BaseAgent):
    """
    Agent for reviewing dependency management and security.

    Reviews:
    - Dependency versions
    - Security vulnerabilities
    - License compliance
    - Outdated packages
    - Dependency conflicts
    - Unnecessary dependencies
    - Supply chain risks
    """

    metadata = AgentMetadata(
        name="dependency_reviewer",
        category="review",
        description="Reviews dependency management and security",
        required_skills=["safety", "pip-audit", "license-checker", " pipdeptree"],
        input_types=["requirements_files", "lock_files"],
        output_types=["dependency_report", "vulnerability_list", "recommendations"],
    )

    async def execute(self, task, context):
        """Execute dependency review."""
        requirements_file = task.parameters.get("requirements_file", "requirements.txt")

        # Check for vulnerabilities
        vulnerability_scan = await self.run_skill(
            "safety",
            operation="check",
            requirements=requirements_file,
        )

        # Audit dependencies
        audit_results = await self.run_skill(
            "pip-audit",
            operation="audit",
            requirements=requirements_file,
        )

        # Check licenses
        license_check = await self.run_skill(
            "license-checker",
            operation="check",
            path="src/",
        )

        # Analyze dependency tree
        dependency_tree = await self.run_skill(
            "pipdeptree",
            operation="analyze",
        )

        # Find outdated packages
        outdated_packages = self._find_outdated_packages(requirements_file)

        return self.format_result(
            {
                "vulnerability_scan": vulnerability_scan,
                "audit_results": audit_results,
                "license_check": license_check,
                "dependency_tree": dependency_tree,
                "outdated_packages": outdated_packages,
                "recommendations": self._generate_dependency_recommendations(
                    vulnerability_scan,
                    license_check,
                    outdated_packages,
                ),
            }
        )

    def _find_outdated_packages(self, requirements_file):
        """Find outdated packages."""
        return {
            "outdated_count": 0,
            "outdated_list": [],
            "major_updates_available": [],
        }

    def _generate_dependency_recommendations(self, vulns, licenses, outdated):
        """Generate dependency recommendations."""
        recommendations = []

        if vulns.get("vulnerabilities"):
            critical = len([v for v in vulns["vulnerabilities"] if v.get("severity") == "critical"])
            recommendations.append(
                {
                    "priority": "critical",
                    "category": "dependency",
                    "action": f"Fix {critical} critical vulnerabilities",
                    "packages": [v["package"] for v in vulns["vulnerabilities"][:5]],
                }
            )

        if licenses.get("violations"):
            recommendations.append(
                {
                    "priority": "high",
                    "category": "dependency",
                    "action": f"Resolve {len(licenses['violations'])} license violations",
                }
            )

        if outdated.get("outdated_count", 0) > 10:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "dependency",
                    "action": f"Update {outdated['outdated_count']} outdated packages",
                }
            )

        return recommendations
