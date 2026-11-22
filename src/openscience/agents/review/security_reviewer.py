"""Security Review Agent for openScience."""

from openscience.core.agent import AgentMetadata, BaseAgent


class SecurityReviewerAgent(BaseAgent):
    """
    Agent for reviewing code security vulnerabilities and best practices.

    Reviews code for:
    - SQL injection vulnerabilities
    - XSS vulnerabilities
    - Authentication/authorization issues
    - Sensitive data exposure
    - Insecure dependencies
    - Code injection risks
    - Cryptographic weaknesses
    - OWASP Top 10 issues
    """

    metadata = AgentMetadata(
        name="security_reviewer",
        category="review",
        description="Reviews code for security vulnerabilities and OWASP compliance",
        required_skills=["bandit", "safety", "semgrep"],
        input_types=["source_code", "dependencies"],
        output_types=["security_report", "vulnerability_list", "recommendations"],
    )

    async def execute(self, task, context):
        """Execute security review."""
        target_path = task.parameters.get("target_path", "src/")

        # Run security scans
        bandit_results = await self.run_skill(
            "bandit",
            operation="scan",
            path=target_path,
            severity=["medium", "high"],
        )

        safety_results = await self.run_skill(
            "safety",
            operation="check",
            requirements="requirements.txt",
        )

        semgrep_results = await self.run_skill(
            "semgrep",
            operation="scan",
            path=target_path,
            rules=["p/security", "p/owasp-top-10"],
        )

        # Analyze and prioritize findings
        vulnerabilities = self._analyze_findings(
            bandit_results,
            safety_results,
            semgrep_results,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(vulnerabilities)

        return self.format_result(
            {
                "vulnerabilities": vulnerabilities,
                "recommendations": recommendations,
                "summary": {
                    "critical": len([v for v in vulnerabilities if v["severity"] == "critical"]),
                    "high": len([v for v in vulnerabilities if v["severity"] == "high"]),
                    "medium": len([v for v in vulnerabilities if v["severity"] == "medium"]),
                    "low": len([v for v in vulnerabilities if v["severity"] == "low"]),
                },
            }
        )

    def _analyze_findings(self, bandit, safety, semgrep):
        """Analyze and categorize security findings."""
        vulnerabilities = []

        # Parse bandit results
        for finding in bandit.get("results", []):
            vulnerabilities.append(
                {
                    "tool": "bandit",
                    "type": "code_vulnerability",
                    "severity": finding.get("issue_severity", "medium").lower(),
                    "file": finding.get("filename"),
                    "line": finding.get("line_number"),
                    "description": finding.get("issue_text"),
                    "cwe": finding.get("issue_cwe"),
                }
            )

        # Parse safety results
        for vuln in safety.get("vulnerabilities", []):
            vulnerabilities.append(
                {
                    "tool": "safety",
                    "type": "dependency_vulnerability",
                    "severity": "high",
                    "package": vuln.get("package"),
                    "installed_version": vuln.get("installed_version"),
                    "fixed_version": vuln.get("fixed_version"),
                    "cve": vuln.get("cve"),
                    "description": vuln.get("description"),
                }
            )

        # Parse semgrep results
        for finding in semgrep.get("results", []):
            vulnerabilities.append(
                {
                    "tool": "semgrep",
                    "type": "pattern_match",
                    "severity": finding.get("extra", {}).get("severity", "medium").lower(),
                    "file": finding.get("path"),
                    "line": finding.get("start", {}).get("line"),
                    "rule": finding.get("check_id"),
                    "description": finding.get("extra", {}).get("message"),
                }
            )

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        vulnerabilities.sort(key=lambda x: severity_order.get(x["severity"], 4))

        return vulnerabilities

    def _generate_recommendations(self, vulnerabilities):
        """Generate actionable recommendations from findings."""
        recommendations = []

        if any(v["severity"] == "critical" for v in vulnerabilities):
            recommendations.append(
                {
                    "priority": "immediate",
                    "action": "Address critical vulnerabilities before deployment",
                    "affected_count": len(
                        [v for v in vulnerabilities if v["severity"] == "critical"]
                    ),
                }
            )

        if any(v["type"] == "dependency_vulnerability" for v in vulnerabilities):
            outdated = {
                v["package"] for v in vulnerabilities if v["type"] == "dependency_vulnerability"
            }
            recommendations.append(
                {
                    "priority": "high",
                    "action": f"Update {len(outdated)} vulnerable dependencies",
                    "packages": list(outdated),
                }
            )

        return recommendations
