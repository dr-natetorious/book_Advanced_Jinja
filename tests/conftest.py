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

from smart_templates import SmartTemplateRegistry, SmartTemplates
from smart_templates.fastapi_integration import (
    SmartFastApiTemplates,
    create_smart_response,
)

# Import test directory constants
from tests import TEST_TEMPLATES_DIR

# Import test models
from tests.models.business_objects import (
    Course,
    Enrollment,
    EnrollmentStatus,
    School,
    Student,
    create_complete_test_data,
    create_sample_school,
    create_sample_student,
)


@pytest.fixture
def templates_dir(tmp_path: Path) -> Path:
    """
    Create a temporary directory with test templates.
    Copies templates from TEST_TEMPLATES_DIR.
    """
    templates_output_dir = tmp_path / "templates"
    templates_output_dir.mkdir(parents=True, exist_ok=True)

    fixtures_templates_source = Path(TEST_TEMPLATES_DIR)

    # Ensure source templates exist and copy them
    if not fixtures_templates_source.exists():
        _create_minimal_templates(templates_output_dir)
        pytest.fail(
            f"TEST_TEMPLATES_DIR '{fixtures_templates_source}' not found. "
            "Cannot set up full test templates. Created minimal fallback."
        )
    else:
        import shutil
        shutil.copytree(
            fixtures_templates_source, templates_output_dir, dirs_exist_ok=True
        )

    return templates_output_dir


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

    # Course templates
    course_dir = templates_dir / "course"
    course_dir.mkdir(exist_ok=True)

    (course_dir / "detail.html").write_text(
        """{% extends "base.html" %}
{% block title %}{{ object.title }} Detail{% endblock %}
{% block content %}
<h1>{{ object.title }} ({{ object.course_code }})</h1>
<p>Description: {{ object.description }}</p>
<p>Instructor: {{ object.instructor_name }}</p>
<p>Enrolled: {{ object.enrolled_students }} / {{ object.max_students }}</p>
{% endblock %}"""
    )

    (course_dir / "instructor_view.html").write_text(
        """{% extends "base.html" %}
{% block title %}{{ object.title }} - Instructor View{% endblock %}
{% block content %}
<h1>Instructor View: {{ object.title }}</h1>
<p>Course Code: {{ object.course_code }}</p>
<p>Enrolled Students: {{ object.enrolled_students }}</p>
<h2>Student List</h2>
{% for enrollment in object.enrollments %}
<p>{{ enrollment.student.name }} - {{ enrollment.status }}</p>
{% endfor %}
{% endblock %}"""
    )

    (course_dir / "student_view.html").write_text(
        """{% extends "base.html" %}
{% block title %}{{ object.course.title }} - Student View{% endblock %}
{% block content %}
<h1>Student View: {{ object.course.title }}</h1>
<p>Your Progress: {{ object.progress_percentage }}%</p>
<p>Status: {{ object.status }}</p>
{% endblock %}"""
    )


@pytest.fixture
def smart_registry() -> SmartTemplateRegistry:
    """Create a SmartTemplateRegistry with test configurations."""
    registry = SmartTemplateRegistry()

    # School templates
    registry.register_simple(School, template_name="school/dashboard.html")
    registry.register_simple(School, template_name="school/list.html", variation="list")

    # Student templates with status variations
    registry.register_simple(Student, template_name="student/profile.html")
    registry.register_simple(
        Student, template_name="student/active.html", variation=EnrollmentStatus.ACTIVE
    )
    registry.register_simple(
        Student,
        template_name="student/completed.html",
        variation=EnrollmentStatus.COMPLETED,
    )
    registry.register_simple(
        Student,
        template_name="student/reattempt.html",
        variation=EnrollmentStatus.REATTEMPT,
    )

    # Course templates
    registry.register_simple(Course, template_name="course/detail.html")
    registry.register_simple(
        Course, template_name="course/instructor_view.html", variation="instructor"
    )
    registry.register_simple(
        Course, template_name="course/student_view.html", variation="student"
    )

    return registry


@pytest.fixture
def smart_templates(
    templates_dir: Path, smart_registry: SmartTemplateRegistry
) -> SmartTemplates:
    """Create a SmartTemplates instance with test configuration."""
    templates = SmartTemplates(
        directory=str(templates_dir),
        registry=smart_registry,
        autoescape=True,
        enable_async=False,
    )
    templates.set_debug_mode(True)
    return templates


@pytest.fixture
def smart_fastapi_templates(
    templates_dir: Path, smart_registry: SmartTemplateRegistry
) -> SmartFastApiTemplates:
    """Create a SmartFastApiTemplates instance for FastAPI testing."""
    templates = SmartFastApiTemplates(
        directory=str(templates_dir),
        registry=smart_registry,
        debug_mode=True,
        autoescape=True,
        enable_async=False,
    )
    return templates


@pytest.fixture
def smart_pytest_templates(
    templates_dir: Path, smart_registry: SmartTemplateRegistry, tmp_path: Path
) -> Any:  # Would be SmartPytestTemplates when implemented
    """Create a SmartPytestTemplates instance for pytest integration testing."""
    try:
        from smart_templates.pytest_integration import SmartPytestTemplates

        templates = SmartPytestTemplates(
            directory=str(templates_dir),
            registry=smart_registry,
            output_dir=str(tmp_path / "test_reports"),
            debug_mode=True,
        )
        return templates
    except ImportError:
        return None


@pytest.fixture
def sample_test_data() -> (
    tuple[list[School], list[Course], list[Student], list[Enrollment]]
):
    """Create complete sample test data using factory functions."""
    return create_complete_test_data()


@pytest.fixture
def sample_schools(
    sample_test_data: tuple[
        list[School], list[Course], list[Student], list[Enrollment]
    ],
) -> list[School]:
    """Extract sample schools from complete test data."""
    schools, _, _, _ = sample_test_data
    return schools


@pytest.fixture
def sample_courses(
    sample_test_data: tuple[
        list[School], list[Course], list[Student], list[Enrollment]
    ],
) -> list[Course]:
    """Extract sample courses from complete test data."""
    _, courses, _, _ = sample_test_data
    return courses


@pytest.fixture
def sample_students(
    sample_test_data: tuple[
        list[School], list[Course], list[Student], list[Enrollment]
    ],
) -> list[Student]:
    """Extract sample students from complete test data."""
    _, _, students, _ = sample_test_data
    return students


@pytest.fixture
def sample_enrollments(
    sample_test_data: tuple[
        list[School], list[Course], list[Student], list[Enrollment]
    ],
) -> list[Enrollment]:
    """Extract sample enrollments from complete test data."""
    _, _, _, enrollments = sample_test_data
    return enrollments


@pytest.fixture
def sample_school() -> School:
    """Create a single sample school for testing."""
    return create_sample_school("Test University", "San Francisco", "CA")


@pytest.fixture
def sample_student() -> Student:
    """Create a single sample student for testing."""
    return create_sample_student("John Doe", major="Computer Science")


@pytest.fixture
def test_fastapi_app(smart_fastapi_templates: SmartFastApiTemplates) -> FastAPI:
    """Create a test FastAPI application with SmartTemplates integration."""
    app = FastAPI(title="SmartTemplates Test App")

    # Create the smart_response decorator
    smart_response = create_smart_response(smart_fastapi_templates)

    @app.get("/")
    async def root():
        return {"message": "Hello from SmartTemplates test app"}

    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "smarttemplates-test"}

    # Business routes using smart_response decorator
    @app.get("/schools/{school_id}")
    @smart_response("school/dashboard.html")
    async def get_school(school_id: int):
        school = create_sample_school(f"Test School {school_id}", "Test City", "CA")
        school.id = school_id
        return school

    @app.get("/schools")
    @smart_response("school/list.html")
    async def list_schools():
        schools = [
            create_sample_school("Tech University", "San Francisco", "CA"),
            create_sample_school("State College", "Austin", "TX"),
        ]
        for i, school in enumerate(schools, 1):
            school.id = i
        return {"schools": schools}

    @app.get("/students/{student_id}")
    @smart_response("student/profile.html")
    async def get_student(student_id: int):
        student = create_sample_student(
            f"Test Student {student_id}", major="Computer Science"
        )
        student.id = student_id
        return student

    @app.get("/courses/{course_id}")
    @smart_response("course/detail.html")
    async def get_course(course_id: int):
        from tests.models.business_objects import create_sample_course
        course = create_sample_course(f"Test Course {course_id}", f"CS{course_id:03d}")
        course.id = course_id
        return course

    # API routes (should return JSON regardless of Accept header)
    @app.get("/api/schools")
    async def api_list_schools():
        schools = [
            create_sample_school("API School 1", "API City", "CA"),
            create_sample_school("API School 2", "API City", "TX"),
        ]
        return {"schools": [s.to_template_dict() for s in schools]}

    # Error routes for testing
    @app.get("/error/template")
    @smart_response("nonexistent/template.html")
    async def template_error():
        return {"message": "This should cause a template error"}

    return app


@pytest.fixture  
def test_client(test_fastapi_app: FastAPI) -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(test_fastapi_app)


@pytest.fixture
def api_test_app() -> FastAPI:
    """Create the full API test application for integration testing."""
    from tests.api.app import app
    return app


@pytest.fixture
def api_test_client(api_test_app: FastAPI) -> TestClient:
    """Create a test client for the full API test application."""
    return TestClient(api_test_app)


@pytest.fixture
def template_context() -> dict[str, Any]:
    """Create a sample template context for testing."""
    return {
        "title": "Test Page",
        "user": {"name": "Test User", "email": "test@example.com"},
        "items": ["item1", "item2", "item3"],
        "debug_mode": True,
        "timestamp": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def render_error_context() -> dict[str, Any]:
    """Create a context that will cause rendering errors for testing."""
    return {
        "undefined_variable": "{{ missing_var }}",
        "invalid_syntax": "{% invalid syntax %}",
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
    assert hasattr(error, "error") and hasattr(
        error.error, "error_type"
    ), "Error object does not have expected structure for error type checking."
    assert (
        error.error.error_type == expected_error_type
    ), f"Expected error type '{expected_error_type}', got '{error.error.error_type}'"


def assert_json_response(response, expected_keys: list[str] = None) -> dict:
    """Assert response is JSON and optionally check for expected keys."""
    assert "application/json" in response.headers.get("content-type", "")
    data = response.json()
    assert isinstance(data, dict)
    
    if expected_keys:
        for key in expected_keys:
            assert key in data, f"Expected key '{key}' not found in JSON response"
    
    return data


def assert_html_response(response, expected_elements: list[str] = None) -> str:
    """Assert response is HTML and optionally check for expected elements."""
    assert "text/html" in response.headers.get("content-type", "")
    content = response.text
    assert "<!DOCTYPE html>" in content or "<html" in content
    
    if expected_elements:
        assert_template_rendered(content, expected_elements)
    
    return content


def assert_smart_response_works(client: TestClient, endpoint: str, object_name: str) -> None:
    """Assert that an endpoint works with both JSON and HTML content negotiation."""
    # Test HTML response
    html_response = client.get(endpoint, headers={"Accept": "text/html"})
    assert html_response.status_code == 200
    html_content = assert_html_response(html_response, [object_name])
    
    # Test JSON response  
    json_response = client.get(endpoint, headers={"Accept": "application/json"})
    assert json_response.status_code == 200
    json_data = assert_json_response(json_response)
    
    # Both should contain the object name in some form
    assert object_name in html_content
    # JSON might have the name in nested structure, so check string representation
    assert object_name in str(json_data)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (slower)"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "business: mark test as business scenario test")
    config.addinivalue_line("markers", "fastapi: mark test as FastAPI related")
    config.addinivalue_line("markers", "templates: mark test as template related")
    config.addinivalue_line("markers", "models: mark test as dependent on business models")
    config.addinivalue_line("markers", "api: mark test as API integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "api" in str(item.fspath):
            item.add_marker(pytest.mark.api)
            item.add_marker(pytest.mark.integration)  # API tests are integration tests

        # Add markers based on test names and business scenarios
        if "fastapi" in item.name.lower():
            item.add_marker(pytest.mark.fastapi)
        if "template" in item.name.lower():
            item.add_marker(pytest.mark.templates)
        if (
            "business" in item.name.lower()
            or "scenario" in item.name.lower()
            or "model" in item.name.lower()
        ):
            item.add_marker(pytest.mark.business)
            item.add_marker(pytest.mark.models)
        if "e2e" in item.name.lower() or "end_to_end" in item.name.lower():
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)