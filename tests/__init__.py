"""
SmartTemplates Test Suite

This package contains comprehensive tests for the SmartTemplates framework,
following pytest best practices and the testing pyramid structure.

Test Structure (mirrors application structure):
- unit/: Fast unit tests for individual components (majority of tests)
- integration/: Slower integration tests for component interaction
- fixtures/: Test data, templates, and shared fixtures
- models/: Business object models for testing scenarios

Test Organization follows the Testing Pyramid:
- Many fast unit tests (80%+)
- Fewer integration tests (15-20%)
- Minimal end-to-end tests (5%)

Pytest Markers:
- @pytest.mark.unit: Unit tests (fast, isolated)
- @pytest.mark.integration: Integration tests (slower)
- @pytest.mark.slow: Long-running tests
- @pytest.mark.business: Business scenario tests

Usage:
    # Run all tests
    pytest

    # Run only fast unit tests
    pytest -m unit

    # Skip slow tests
    pytest -m "not slow"

    # Run with coverage
    pytest --cov=smart_templates

    # Run specific test file
    pytest tests/unit/test_core.py
"""

# Test configuration paths - relative to project root
TEST_TEMPLATES_DIR = "tests/fixtures/templates"
TEST_DATA_DIR = "tests/fixtures/data"
TEST_OUTPUT_DIR = "test_output"
