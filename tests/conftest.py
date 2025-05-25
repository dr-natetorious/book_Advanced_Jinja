"""
Pytest configuration and shared fixtures for SmartTemplates tests.

This module provides reusable test fixtures, utilities, and configuration
for testing the SmartTemplates framework across all test modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from smart_templates.core import SmartTemplateRegistry, SmartTemplates
from smart_templates.fastapi_integration import SmartFastApiTemplates, create_smart_response

# Import test directory constants
from tests import TEST_TEMPLATES_DIR, TEST_DATA_DIR, TEST_OUTPUT_DIR

# Import test models - corrected import path
try:
    from tests.models.business_objects import (
        Course,
        CourseStatus,
        Enrollment,
        EnrollmentStatus,
        School,
        Student,
        create_complete_test_data,
        create_sample_course,
        create_sample_enrollment,
        create_sample_school,
        create_sample_student,
    )
    
    models_available = True
except ImportError:
    # Handle case where test models aren't available yet
    School = Course = Student = Enrollment = None
    EnrollmentStatus = CourseStatus = None
    create_complete_test_data = None
    create_sample_school = create_sample_course = None
    create_sample_student = create_sample_enrollment = None
    models_available = False


@pytest.fixture
def templates_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with test templates."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy templates from fixtures to temp directory
    fixtures_templates = Path(TEST_TEMPLATES_DIR)
    if fixtures_templates.exists():
        import shutil
        shutil.copytree(fixtures_templates, templates_dir, dirs_exist_ok=True)
    else:
        # Create minimal templates for testing
        _create_minimal_templates(templates_dir)
    
    return templates_dir


def _create_minimal_templates(templates_dir: Path) -> None:
    """Create minimal template files for testing when fixtures aren't available."""
    # Base template
    (templates_dir / "base.html").write_text(
        """<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}SmartTemplates Test{% endblock %}</title>
</head>
<body>
    {% block content %}
    <h1>Test Template</h1>
    {% endblock %}
</body>
</html>"""
    )
    
    # Error template
    (templates_dir / "error.html").write_text(
        """{% extends "base.html" %}
{% block title %}Error{% endblock %}
{% block content %}
<h1>Error Occurred</h1>
<p>{{ error.error.message if error else "Unknown error" }}</p>
{% if debug_mode and error %}
<pre>{{ error.error.stack_trace | join('\\n') if error.error.stack_trace }}</pre>
{% endif %}
{% endblock %}"""
    )
    
    # School templates
    school_dir = templates_dir / "school"
    school_dir.mkdir(exist_ok=True)
    
    (school_dir / "dashboard.html").write_text(
        """{% extends "base.html" %}
{% block title %}{{ object.name }} Dashboard{% endblock %}
{% block content %}
<h1>{{ object.name }}</h1>
<p>Address: {{ object.full_address }}</p>
<p>Total Students: {{ object.total_students }}</p>
<h2>Courses ({{ object.courses | length }})</h2>
<ul>
{% for course in object.courses %}
    <li>{{ course.title }} ({{ course.course_code }})</li>
{% endfor %}
</ul>
{% endblock %}"""
    )
    
    (school_dir / "list.html").write_text(
        """{% extends "base.html" %}
{% block title %}Schools{% endblock %}
{% block content %}
<h1>All Schools</h1>
<ul>
{% for school in schools %}
    <li>{{ school.name }} - {{ school.city }}, {{ school.state }}</li>
{% endfor %}
</ul>
{% endblock %}"""
    )
    
    # Student templates with status variations
    student_dir = templates_dir / "student"
    student_dir.mkdir(exist_ok=True)
    
    (student_dir / "profile.html").write_text(
        """{% extends "base.html" %}
{% block title %}{{ object.name }} Profile{% endblock %}
{% block content %}
<h1>{{ object.name }}</h1>
<p>Email: {{ object.email }}</p>
<p>Major: {{ object.major }}</p>
<p>GPA: {{ object.gpa }}</p>
<h2>Enrollments</h2>
<ul>
{% for enrollment in object.enrollments %}
    <li>{{ enrollment.course.title }} - Status: {{ enrollment.status }} ({{ enrollment.progress_percentage }}%)</li>
{% endfor %}
</ul>
{% endblock %}"""
    )
    
    # Status-specific student templates
    (student_dir / "active.html").write_text(
        """{% extends "base.html" %}
{% block title %}Active Student: {{ object.name }}{% endblock %}
{% block content %}
<h1>{{ object.name }} - Active Status</h1>
<p>Currently enrolled in {{ object.active_courses | length }} courses</p>
<div class="alert alert-success">Student is actively participating</div>
{% endblock %}"""
    )
    
    (student_dir / "completed.html").write_text(
        """{% extends "base.html" %}
{% block title %}Graduate: {{ object.name }}{% endblock %}
{% block content %}
<h1>{{ object.name }} - Completed</h1>
<p>Successfully completed {{ object.completed_courses | length }} courses</p>
<div class="alert alert-info">Student has graduated</div>
{% endblock %}"""
    )
    
    (student_dir / "reattempt.html").write_text(
        """{% extends "base.html" %}
{% block title %}{{ object.name }} - Needs Support{% endblock %}
{% block content %}
<h1>{{ object.name }} - Reattempt Status</h1>
<div class="alert alert-warning">Student needs additional support</div>
{% endblock %}"""
    )


@pytest.fixture
def smart_registry() -> SmartTemplateRegistry:
    """Create a SmartTemplateRegistry with test configurations."""
    registry = SmartTemplateRegistry()
    
    # Register template mappings if models are available
    if models_available:
        # School templates
        registry.register(School, template_name="school/dashboard.html")
        registry.register(School, template_name="school/list.html", variation="list")
        
        # Student templates with status variations
        registry.register(Student, template_name="student/profile.html")
        registry.register(Student, template_name="student/active.html", variation=EnrollmentStatus.ACTIVE)
        registry.register(Student, template_name="student/completed.html", variation=EnrollmentStatus.COMPLETED)
        registry.register(Student, template_name="student/reattempt.html", variation=EnrollmentStatus.REATTEMPT)
        
        # Course templates
        registry.register(Course, template_name="course/detail.html")
        registry.register(Course, template_name="course/instructor_view.html", variation="instructor")
        registry.register(Course, template_name="course/student_view.html", variation="student")
    
    return registry


@pytest.fixture
def smart_templates(templates_dir: Path, smart_registry: SmartTemplateRegistry) -> SmartTemplates:
    """Create a SmartTemplates instance with test configuration."""
    templates = SmartTemplates(
        directory=str(templates_dir),
        registry=smart_registry,
        autoescape=True,
        enable_async=False
    )
    templates.set_debug_mode(True)
    return templates


@pytest.fixture
def smart_fastapi_templates(
    templates_dir: Path, 
    smart_registry: SmartTemplateRegistry
) -> SmartFastApiTemplates:
    """Create a SmartFastApiTemplates instance for FastAPI testing."""
    templates = SmartFastApiTemplates(
        directory=str(templates_dir),
        registry=smart_registry,
        autoescape=True,
        enable_async=False
    )
    templates.set_debug_mode(True)
    return templates


@pytest.fixture
def smart_pytest_templates(
    templates_dir: Path, 
    smart_registry: SmartTemplateRegistry,
    tmp_path: Path
) -> Any:  # Would be SmartPytestTemplates when implemented
    """Create a SmartPytestTemplates instance for pytest integration testing."""
    # This will be implemented when SmartPytestTemplates is created
    try:
        from smart_templates.pytest_integration import SmartPytestTemplates
        templates = SmartPytestTemplates(
            directory=str(templates_dir),
            registry=smart_registry,
            output_dir=str(tmp_path / "test_reports"),
            debug_mode=True
        )
        return templates
    except ImportError:
        # Return None if not implemented yet
        return None


@pytest.fixture
def sample_test_data() -> tuple[list[Any], list[Any], list[Any], list[Any]]:
    """Create complete sample test data using factory functions."""
    if models_available and create_complete_test_data:
        return create_complete_test_data()
    return [], [], [], []


@pytest.fixture
def sample_schools(sample_test_data: tuple[list[Any], list[Any], list[Any], list[Any]]) -> list[Any]:
    """Extract sample schools from complete test data."""
    schools, _, _, _ = sample_test_data
    return schools


@pytest.fixture
def sample_courses(sample_test_data: tuple[list[Any], list[Any], list[Any], list[Any]]) -> list[Any]:
    """Extract sample courses from complete test data."""
    _, courses, _, _ = sample_test_data
    return courses


@pytest.fixture
def sample_students(sample_test_data: tuple[list[Any], list[Any], list[Any], list[Any]]) -> list[Any]:
    """Extract sample students from complete test data."""
    _, _, students, _ = sample_test_data
    return students


@pytest.fixture
def sample_enrollments(sample_test_data: tuple[list[Any], list[Any], list[Any], list[Any]]) -> list[Any]:
    """Extract sample enrollments from complete test data."""
    _, _, _, enrollments = sample_test_data
    return enrollments


@pytest.fixture
def sample_school() -> Any:
    """Create a single sample school for testing."""
    if models_available and create_sample_school:
        return create_sample_school("Test University", "San Francisco", "CA")
    return None


@pytest.fixture
def sample_student() -> Any:
    """Create a single sample student for testing."""
    if models_available and create_sample_student:
        return create_sample_student("John Doe", major="Computer Science")
    return None


@pytest.fixture
def test_fastapi_app(smart_fastapi_templates: SmartFastApiTemplates) -> FastAPI:
    """Create a test FastAPI application with SmartTemplates integration."""
    app = FastAPI(title="SmartTemplates Test App")
    
    # Create the smart_response decorator
    smart_response = create_smart_response(smart_fastapi_templates)
    
    @app.get("/")
    async def root(request):
        return {"message": "Hello from SmartTemplates test app"}
    
    @app.get("/health")
    async def health(request):
        return {"status": "healthy", "service": "smarttemplates-test"}
    
    # Add business routes if models are available
    if models_available:
        @app.get("/schools/{school_id}")
        @smart_response("school/dashboard.html")
        async def get_school(request, school_id: int):
            # Create a test school with realistic data
            school = create_sample_school(f"Test School {school_id}", "Test City", "CA")
            school.id = school_id
            return school
        
        @app.get("/schools")
        @smart_response("school/list.html")
        async def list_schools(request):
            schools = [
                create_sample_school("Tech University", "San Francisco", "CA"),
                create_sample_school("State College", "Austin", "TX"),
            ]
            for i, school in enumerate(schools, 1):
                school.id = i
            return {"schools": schools}
        
        @app.get("/students/{student_id}")
        @smart_response("student/profile.html")
        async def get_student(request, student_id: int):
            student = create_sample_student(f"Test Student {student_id}", major="Computer Science")
            student.id = student_id
            return student
    
    return app


@pytest.fixture
def test_client(test_fastapi_app: FastAPI) -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(test_fastapi_app)


@pytest.fixture
def template_context() -> dict[str, Any]:
    """Create a sample template context for testing."""
    return {
        "title": "Test Page",
        "user": {"name": "Test User", "email": "test@example.com"},
        "items": ["item1", "item2", "item3"],
        "debug_mode": True,
        "timestamp": "2025-01-01T00:00:00Z"
    }


@pytest.fixture
def render_error_context() -> dict[str, Any]:
    """Create a context that will cause rendering errors for testing."""
    return {
        "undefined_variable": "{{ missing_var }}",
        "invalid_syntax": "{% invalid syntax %}"
    }


# Utility functions for tests
def assert_template_rendered(content: str, expected_elements: list[str]) -> None:
    """Assert that template content contains expected elements."""
    for element in expected_elements:
        assert element in content, f"Expected '{element}' not found in rendered content"


def assert_no_template_errors(error: Any) -> None:
    """Assert that no template rendering errors occurred."""
    assert error is None, f"Unexpected template error: {error}"


def assert_template_error(error: Any, expected_error_type: str) -> None:
    """Assert that a template error occurred with expected type."""
    assert error is not None, "Expected template error but none occurred"
    assert error.error.error_type == expected_error_type, \
        f"Expected error type '{expected_error_type}', got '{error.error.error_type}'"


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (slower)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "business: mark test as business scenario test"
    )
    config.addinivalue_line(
        "markers", "fastapi: mark test as FastAPI related"
    )
    config.addinivalue_line(
        "markers", "templates: mark test as template related"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add markers based on test names and business scenarios
        if "fastapi" in item.name.lower():
            item.add_marker(pytest.mark.fastapi)
        if "template" in item.name.lower():
            item.add_marker(pytest.mark.templates)
        if "business" in item.name.lower() or "scenario" in item.name.lower():
            item.add_marker(pytest.mark.business)