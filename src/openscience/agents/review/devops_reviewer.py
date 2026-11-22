"""DevOps Review Agent for openScience."""

from openscience.core.agent import AgentMetadata, BaseAgent


class DevOpsReviewerAgent(BaseAgent):
    """
    Agent for reviewing DevOps practices and infrastructure.

    Reviews:
    - Docker best practices
    - CI/CD pipeline configuration
    - Infrastructure as Code
    - Monitoring and logging
    - Security scanning
    - Deployment strategies
    - Resource optimization
    """

    metadata = AgentMetadata(
        name="devops_reviewer",
        category="review",
        description="Reviews DevOps practices and infrastructure configuration",
        required_skills=["hadolint", "trivy", "checkov", "kube-score"],
        input_types=["dockerfiles", "ci_configs", "infrastructure_code"],
        output_types=["devops_report", "security_findings", "recommendations"],
    )

    async def execute(self, task, context):
        """Execute DevOps review."""
        docker_path = task.parameters.get("docker_path", "docker/")

        # Lint Dockerfiles
        docker_lint = await self.run_skill(
            "hadolint",
            operation="lint",
            path=docker_path,
        )

        # Scan for vulnerabilities
        vulnerability_scan = await self.run_skill(
            "trivy",
            operation="scan",
            target=".",
        )

        # Check IaC configurations
        iac_check = await self.run_skill(
            "checkov",
            operation="scan",
            path=".",
        )

        # Analyze CI/CD configuration
        cicd_analysis = self._analyze_cicd()

        return self.format_result(
            {
                "docker_lint": docker_lint,
                "vulnerability_scan": vulnerability_scan,
                "iac_check": iac_check,
                "cicd_analysis": cicd_analysis,
                "recommendations": self._generate_devops_recommendations(
                    docker_lint,
                    vulnerability_scan,
                    iac_check,
                ),
            }
        )

    def _analyze_cicd(self):
        """Analyze CI/CD pipeline configuration."""
        return {
            "pipeline_stages": 0,
            "test_coverage_gates": False,
            "security_scans_enabled": False,
            "deployment_gates": [],
        }

    def _generate_devops_recommendations(self, docker, vulns, iac):
        """Generate DevOps recommendations."""
        recommendations = []

        if docker.get("violations"):
            recommendations.append(
                {
                    "priority": "high",
                    "category": "devops",
                    "action": f"Fix {len(docker['violations'])} Dockerfile issues",
                }
            )

        if vulns.get("vulnerabilities"):
            critical = len([v for v in vulns["vulnerabilities"] if v.get("severity") == "CRITICAL"])
            recommendations.append(
                {
                    "priority": "critical",
                    "category": "devops",
                    "action": f"Fix {critical} critical vulnerabilities in containers",
                }
            )

        if iac.get("failed_checks"):
            recommendations.append(
                {
                    "priority": "high",
                    "category": "devops",
                    "action": f"Address {len(iac['failed_checks'])} IaC security issues",
                }
            )

        return recommendations
