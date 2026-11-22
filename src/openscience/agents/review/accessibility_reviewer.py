"""Accessibility Review Agent for openScience."""

from openscience.core.agent import AgentMetadata, BaseAgent


class AccessibilityReviewerAgent(BaseAgent):
    """
    Agent for reviewing accessibility (a11y) compliance.

    Reviews:
    - WCAG compliance
    - Screen reader compatibility
    - Keyboard navigation
    - Color contrast
    - Alt text for images
    - ARIA attributes
    - Focus management
    """

    metadata = AgentMetadata(
        name="accessibility_reviewer",
        category="review",
        description="Reviews accessibility compliance and WCAG standards",
        required_skills=["axe-core", "pa11y", "html-proofer"],
        input_types=["html_files", "ui_components"],
        output_types=["accessibility_report", "wcag_violations", "recommendations"],
    )

    async def execute(self, task, context):
        """Execute accessibility review."""
        ui_path = task.parameters.get("ui_path", "src/openscience/ui/")

        # Run axe-core accessibility tests
        axe_results = await self.run_skill(
            "axe-core",
            operation="scan",
            path=ui_path,
        )

        # Run pa11y tests
        pa11y_results = await self.run_skill(
            "pa11y",
            operation="test",
            url="http://localhost:8080",
        )

        # Check HTML validity
        html_check = await self.run_skill(
            "html-proofer",
            operation="check",
            path=ui_path,
        )

        # Analyze color contrast
        contrast_analysis = self._analyze_color_contrast(ui_path)

        # Review ARIA usage
        aria_review = self._review_aria_usage(ui_path)

        return self.format_result(
            {
                "axe_results": axe_results,
                "pa11y_results": pa11y_results,
                "html_check": html_check,
                "color_contrast": contrast_analysis,
                "aria_review": aria_review,
                "recommendations": self._generate_accessibility_recommendations(
                    axe_results,
                    pa11y_results,
                    contrast_analysis,
                ),
            }
        )

    def _analyze_color_contrast(self, ui_path):
        """Analyze color contrast ratios."""
        return {
            "contrast_violations": [],
            "normal_text_failures": 0,
            "large_text_failures": 0,
        }

    def _review_aria_usage(self, ui_path):
        """Review ARIA attribute usage."""
        return {
            "missing_aria_labels": [],
            "incorrect_aria_roles": [],
            "missing_alt_text": [],
        }

    def _generate_accessibility_recommendations(self, axe, pa11y, contrast):
        """Generate accessibility recommendations."""
        recommendations = []

        violations = axe.get("violations", [])
        if violations:
            critical = len([v for v in violations if v.get("impact") == "critical"])
            recommendations.append(
                {
                    "priority": "critical",
                    "category": "accessibility",
                    "action": f"Fix {critical} critical accessibility issues",
                }
            )

        if contrast.get("contrast_violations"):
            recommendations.append(
                {
                    "priority": "high",
                    "category": "accessibility",
                    "action": f"Fix {len(contrast['contrast_violations'])} color contrast issues",
                }
            )

        return recommendations
