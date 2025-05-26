"""Pytest integration for SmartTemplates - Test automation and reporting."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .core import RenderError, SmartTemplateRegistry, SmartTemplates, TemplateErrorDetail

try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False


class SmartPytestTemplates(SmartTemplates):
    """
    Pytest-specific extension of SmartTemplates that adds test automation capabilities,
    fixture generation, test case creation, and documentation generation.
    """

    def __init__(
        self,
        directory: str,
        *,
        registry: SmartTemplateRegistry | None = None,
        debug_mode: bool = False,
        output_dir: str = "test_reports",
        **kwargs: Any,
    ) -> None:
        """
        Initialize SmartPytestTemplates.

        Args:
            directory: Template directory path
            registry: Template registry instance
            debug_mode: Enable debug mode for enhanced error reporting
            output_dir: Directory for generated test files and reports
            **kwargs: Additional Jinja2 environment options
        """
        super().__init__(directory, registry=registry, debug_mode=debug_mode, **kwargs)
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _prepare_test_context(self, base_context: dict[str, Any]) -> dict[str, Any]:
        """Prepare context with pytest-specific variables."""
        # CRITICAL: Defensive copy - never mutate input
        template_context = base_context.copy()
        template_context.setdefault("debug_mode", self.debug_mode)
        template_context.setdefault("timestamp", datetime.now())
        template_context.setdefault("output_dir", str(self.output_dir))
        
        # Add pytest version if available
        if PYTEST_AVAILABLE:
            template_context.setdefault("pytest_version", pytest.__version__)
        else:
            template_context.setdefault("pytest_version", "not_available")
        
        return template_context

    def _write_output_file(self, content: str, filepath: Path) -> bool:
        """Write generated content to file with error handling."""
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            self._logger.info(f"Generated test file: {filepath}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to write file {filepath}: {e}")
            return False

    def generate_test_report(
        self,
        test_results: dict[str, Any],
        *,
        template_name: str = "test_report.html",
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:
        """
        Generate test execution reports from pytest results.

        Args:
            test_results: Dictionary containing test execution data
            template_name: Template to use for report generation
            output_file: Optional output file path

        Returns:
            Tuple of (rendered_content, error_or_none)
        """
        try:
            # CRITICAL: Defensive copy of input context
            template_context = self._prepare_test_context(test_results)

            # Add test-specific context
            template_context.setdefault("report_type", "test_execution")
            template_context.setdefault(
                "total_tests", len(test_results.get("tests", []))
            )
            template_context.setdefault(
                "passed_tests",
                len(
                    [
                        t
                        for t in test_results.get("tests", [])
                        if t.get("status") == "passed"
                    ]
                ),
            )
            template_context.setdefault(
                "failed_tests",
                len(
                    [
                        t
                        for t in test_results.get("tests", [])
                        if t.get("status") == "failed"
                    ]
                ),
            )

            content, error = self.render_safe(template_name, template_context)

            if error:
                self._logger.error(
                    f"Failed to render test report template: {error.error.message}"
                )
                return "", error

            if output_file:
                output_path = self.output_dir / output_file
                if self._write_output_file(content, output_path):
                    self._logger.info(f"Test report written to: {output_path}")

            return content, None

        except Exception as e:
            self._logger.exception("Unexpected error in test report generation")
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=template_name,
                context_data=self._extract_context_types(test_results),
            )
            return "", RenderError(error=error)

    def generate_pytest_fixtures(
        self,
        model_objects: list[Any],
        *,
        fixture_template: str = "fixtures.py.j2",
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:
        """
        Generate pytest fixtures from business objects.

        Args:
            model_objects: List of model objects to create fixtures for
            fixture_template: Template to use for fixture generation
            output_file: Optional output file path

        Returns:
            Tuple of (rendered_content, error_or_none)
        """
        try:
            base_context = {
                "objects": model_objects,
                "fixture_type": "pytest_fixtures",
                "object_types": list(set(type(obj).__name__ for obj in model_objects)),
            }

            # CRITICAL: Defensive copy through _prepare_test_context
            template_context = self._prepare_test_context(base_context)

            content, error = self.render_safe(fixture_template, template_context)

            if error:
                self._logger.error(
                    f"Failed to render pytest fixtures template: {error.error.message}"
                )
                return "", error

            if output_file:
                output_path = self.output_dir / output_file
                if self._write_output_file(content, output_path):
                    self._logger.info(f"Pytest fixtures written to: {output_path}")

            return content, None

        except Exception as e:
            self._logger.exception("Unexpected error in pytest fixture generation")
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=fixture_template,
                context_data={"object_count": len(model_objects)},
            )
            return "", RenderError(error=error)

    def generate_test_cases(
        self,
        objects: list[Any],
        *,
        test_template: str = "test_cases.py.j2",
        parametrize: bool = True,
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:
        """
        Generate parametrized test cases from objects.

        Args:
            objects: List of objects to create test cases for
            test_template: Template to use for test case generation
            parametrize: Whether to use pytest.mark.parametrize
            output_file: Optional output file path

        Returns:
            Tuple of (rendered_content, error_or_none)
        """
        try:
            base_context = {
                "test_objects": objects,
                "parametrize": parametrize,
                "test_type": "parametrized" if parametrize else "individual",
                "object_types": list(set(type(obj).__name__ for obj in objects)),
            }

            # CRITICAL: Defensive copy through _prepare_test_context
            template_context = self._prepare_test_context(base_context)

            content, error = self.render_safe(test_template, template_context)

            if error:
                self._logger.error(
                    f"Failed to render test cases template: {error.error.message}"
                )
                return "", error

            if output_file:
                output_path = self.output_dir / output_file
                if self._write_output_file(content, output_path):
                    self._logger.info(f"Test cases written to: {output_path}")

            return content, None

        except Exception as e:
            self._logger.exception("Unexpected error in test case generation")
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=test_template,
                context_data={"object_count": len(objects)},
            )
            return "", RenderError(error=error)

    def generate_test_documentation(
        self,
        test_data: dict[str, Any],
        *,
        doc_template: str = "test_docs.md",
        format_type: str = "markdown",
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:
        """
        Generate test documentation from templates.

        Args:
            test_data: Dictionary containing test information
            doc_template: Template to use for documentation generation
            format_type: Format type (markdown, html, etc.)
            output_file: Optional output file path

        Returns:
            Tuple of (rendered_content, error_or_none)
        """
        try:
            # CRITICAL: Create copy before modifying
            base_context = test_data.copy()
            base_context.setdefault("format_type", format_type)
            base_context.setdefault("doc_type", "test_documentation")

            # CRITICAL: Defensive copy through _prepare_test_context
            template_context = self._prepare_test_context(base_context)

            content, error = self.render_safe(doc_template, template_context)

            if error:
                self._logger.error(
                    f"Failed to render test documentation template: {error.error.message}"
                )
                return "", error

            if output_file:
                output_path = self.output_dir / output_file
                if self._write_output_file(content, output_path):
                    self._logger.info(f"Test documentation written to: {output_path}")

            return content, None

        except Exception as e:
            self._logger.exception("Unexpected error in test documentation generation")
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=doc_template,
                context_data=self._extract_context_types(test_data),
            )
            return "", RenderError(error=error)

    def generate_mock_objects(
        self,
        object_specs: list[dict[str, Any]],
        *,
        mock_template: str = "mock_objects.py.j2",
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:
        """
        Generate mock objects for testing from specifications.

        Args:
            object_specs: List of dictionaries specifying object properties
            mock_template: Template to use for mock generation
            output_file: Optional output file path

        Returns:
            Tuple of (rendered_content, error_or_none)
        """
        try:
            base_context = {
                "mock_specs": object_specs,
                "mock_type": "pytest_mocks",
                "spec_count": len(object_specs),
            }

            # CRITICAL: Defensive copy through _prepare_test_context
            template_context = self._prepare_test_context(base_context)

            content, error = self.render_safe(mock_template, template_context)

            if error:
                self._logger.error(
                    f"Failed to render mock objects template: {error.error.message}"
                )
                return "", error

            if output_file:
                output_path = self.output_dir / output_file
                if self._write_output_file(content, output_path):
                    self._logger.info(f"Mock objects written to: {output_path}")

            return content, None

        except Exception as e:
            self._logger.exception("Unexpected error in mock object generation")
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=mock_template,
                context_data={"spec_count": len(object_specs)},
            )
            return "", RenderError(error=error)

    def generate_api_tests(
        self,
        api_endpoints: list[dict[str, Any]],
        *,
        api_test_template: str = "api_tests.py.j2",
        include_auth: bool = False,
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:
        """
        Generate API test cases from endpoint specifications.

        Args:
            api_endpoints: List of API endpoint specifications
            api_test_template: Template to use for API test generation
            include_auth: Whether to include authentication in tests
            output_file: Optional output file path

        Returns:
            Tuple of (rendered_content, error_or_none)
        """
        try:
            base_context = {
                "endpoints": api_endpoints,
                "include_auth": include_auth,
                "test_type": "api_tests",
                "endpoint_count": len(api_endpoints),
                "methods": list(set(ep.get("method", "GET") for ep in api_endpoints)),
            }

            # CRITICAL: Defensive copy through _prepare_test_context
            template_context = self._prepare_test_context(base_context)

            content, error = self.render_safe(api_test_template, template_context)

            if error:
                self._logger.error(
                    f"Failed to render API tests template: {error.error.message}"
                )
                return "", error

            if output_file:
                output_path = self.output_dir / output_file
                if self._write_output_file(content, output_path):
                    self._logger.info(f"API tests written to: {output_path}")

            return content, None

        except Exception as e:
            self._logger.exception("Unexpected error in API test generation")
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=api_test_template,
                context_data={"endpoint_count": len(api_endpoints)},
            )
            return "", RenderError(error=error)

    def generate_performance_tests(
        self,
        performance_specs: list[dict[str, Any]],
        *,
        perf_template: str = "performance_tests.py.j2",
        framework: str = "pytest-benchmark",
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:
        """
        Generate performance test cases from specifications.

        Args:
            performance_specs: List of performance test specifications
            perf_template: Template to use for performance test generation
            framework: Performance testing framework to use
            output_file: Optional output file path

        Returns:
            Tuple of (rendered_content, error_or_none)
        """
        try:
            base_context = {
                "perf_specs": performance_specs,
                "framework": framework,
                "test_type": "performance_tests",
                "spec_count": len(performance_specs),
            }

            # CRITICAL: Defensive copy through _prepare_test_context
            template_context = self._prepare_test_context(base_context)

            content, error = self.render_safe(perf_template, template_context)

            if error:
                self._logger.error(
                    f"Failed to render performance tests template: {error.error.message}"
                )
                return "", error

            if output_file:
                output_path = self.output_dir / output_file
                if self._write_output_file(content, output_path):
                    self._logger.info(f"Performance tests written to: {output_path}")

            return content, None

        except Exception as e:
            self._logger.exception("Unexpected error in performance test generation")
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=perf_template,
                context_data={"spec_count": len(performance_specs)},
            )
            return "", RenderError(error=error)

    def generate_test_matrix(
        self,
        matrix_config: dict[str, Any],
        *,
        matrix_template: str = "test_matrix.py.j2",
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:
        """
        Generate test matrix for cross-platform/cross-version testing.

        Args:
            matrix_config: Configuration for test matrix generation
            matrix_template: Template to use for matrix generation
            output_file: Optional output file path

        Returns:
            Tuple of (rendered_content, error_or_none)
        """
        try:
            # CRITICAL: Create copy before modifying
            base_context = matrix_config.copy()
            base_context.setdefault("matrix_type", "cross_platform")

            # CRITICAL: Defensive copy through _prepare_test_context
            template_context = self._prepare_test_context(base_context)

            content, error = self.render_safe(matrix_template, template_context)

            if error:
                self._logger.error(
                    f"Failed to render test matrix template: {error.error.message}"
                )
                return "", error

            if output_file:
                output_path = self.output_dir / output_file
                if self._write_output_file(content, output_path):
                    self._logger.info(f"Test matrix written to: {output_path}")

            return content, None

        except Exception as e:
            self._logger.exception("Unexpected error in test matrix generation")
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=matrix_template,
                context_data=self._extract_context_types(matrix_config),
            )
            return "", RenderError(error=error)


# Usage examples:
# 
# # Basic test report generation
# pytest_templates = SmartPytestTemplates("test_templates/")
# content, error = pytest_templates.generate_test_report(
#     test_results, 
#     output_file="report.html"
# )
#
# # Generate fixtures from business objects
# content, error = pytest_templates.generate_pytest_fixtures(
#     [user1, user2, order1],
#     output_file="conftest.py"
# )
#
# # Generate parametrized test cases
# content, error = pytest_templates.generate_test_cases(
#     business_objects,
#     parametrize=True,
#     output_file="test_generated.py"
# )