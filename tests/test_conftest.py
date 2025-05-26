# tests/test_conftests.py

from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import necessary types from your application and conftest for assertions
from smart_templates.core import SmartTemplateRegistry, SmartTemplates
from smart_templates.fastapi_integration import SmartFastApiTemplates
from tests.conftest import (  # Import the utility functions from conftest
    assert_no_template_errors,
    assert_template_error,
    assert_template_rendered,
)

# Import business objects for type checking (these are assumed to be available
# due to the previous conftest.py refactoring that removed the try-except)
from university.models.business_objects import (
    Course,
    Enrollment,
    EnrollmentStatus,
    School,
    Student,
    create_sample_course,
    create_sample_school,
    create_sample_student,
)


@pytest.mark.templates
def test_templates_dir_fixture(templates_dir: Path, tmp_path: Path):
    """
    Test that the templates_dir fixture creates a temporary directory
    and copies expected files into it.
    """
    assert templates_dir.is_dir()
    assert templates_dir == tmp_path / "templates"

    # Check for presence of key files that should be copied or created minimally
    assert (templates_dir / "base.html").exists()
    assert (templates_dir / "error.html").exists()
    assert (templates_dir / "school" / "dashboard.html").exists()
    assert (templates_dir / "student" / "profile.html").exists()
    assert (templates_dir / "student" / "active.html").exists()


@pytest.mark.templates
@pytest.mark.models  # Mark this as dependent on business models
def test_smart_registry_fixture(smart_registry: SmartTemplateRegistry):
    """
    Test that the smart_registry fixture returns a SmartTemplateRegistry instance
    and has the expected models registered.
    """
    assert isinstance(smart_registry, SmartTemplateRegistry)

    # Corrected: Use find_template and extract the path attribute.
    # find_template expects an object instance, create dummy ones.
    # For School, default variation
    school_obj = create_sample_school()
    mapping = smart_registry.find_template(school_obj)
    assert mapping is not None
    assert mapping["path"] == "school/dashboard.html"
    assert mapping["type"] == "template"

    # For School, 'list' variation
    mapping = smart_registry.find_template(school_obj, variation="list")
    assert mapping is not None
    assert mapping["path"] == "school/list.html"
    assert mapping["type"] == "template"

    # For Student, default variation
    student_obj = create_sample_student()
    mapping = smart_registry.find_template(student_obj)
    assert mapping is not None
    assert mapping["path"] == "student/profile.html"
    assert mapping["type"] == "template"

    # For Student, ACTIVE variation
    mapping = smart_registry.find_template(
        student_obj, variation=EnrollmentStatus.ACTIVE
    )
    assert mapping is not None
    assert mapping["path"] == "student/active.html"
    assert mapping["type"] == "template"

    # For Course, 'instructor' variation
    course_obj = create_sample_course()
    mapping = smart_registry.find_template(course_obj, variation="instructor")
    assert mapping is not None
    assert mapping["path"] == "course/instructor_view.html"
    assert mapping["type"] == "template"


@pytest.mark.templates
def test_smart_templates_fixture(smart_templates: SmartTemplates, templates_dir: Path):
    """
    Test that the smart_templates fixture returns a SmartTemplates instance
    with the correct initial configuration.
    """
    assert isinstance(smart_templates, SmartTemplates)
    # Corrected: Accessing the directory via the Jinja2 environment's loader
    # The FileSystemLoader's searchpath is a list of directories.
    assert smart_templates.env.loader.searchpath == [str(templates_dir)]
    assert (
        smart_templates.env.autoescape is True
    )  # This is passed to self.env but not directly stored
    assert (
        smart_templates.env.is_async is False
    )  # This is passed to self.env but not directly stored
    # Corrected: attribute is 'debug_mode', not '_debug_mode'
    assert smart_templates.debug_mode is True


@pytest.mark.fastapi
@pytest.mark.templates
def test_smart_fastapi_templates_fixture(
    smart_fastapi_templates: SmartFastApiTemplates, templates_dir: Path
):
    """
    Test that the smart_fastapi_templates fixture returns a SmartFastApiTemplates instance
    with the correct initial configuration.
    """
    assert isinstance(smart_fastapi_templates, SmartFastApiTemplates)
    assert smart_fastapi_templates.env.loader.searchpath == [str(templates_dir)]
    assert smart_fastapi_templates.env.autoescape is True
    assert smart_fastapi_templates.env.is_async is False
    assert smart_fastapi_templates.debug_mode is True


@pytest.mark.templates
def test_smart_pytest_templates_fixture(smart_pytest_templates: Any):
    """
    Test the smart_pytest_templates fixture. If SmartPytestTemplates is not
    available, it should return None. Otherwise, it should return an instance.
    """
    if smart_pytest_templates is None:
        pytest.skip("SmartPytestTemplates not installed/available for testing.")
    else:
        # Assuming SmartPytestTemplates exists and is importable
        from smart_templates.pytest_integration import SmartPytestTemplates

        assert isinstance(smart_pytest_templates, SmartPytestTemplates)
        assert hasattr(smart_pytest_templates, "output_dir")
        assert smart_pytest_templates.debug_mode is True


@pytest.mark.models
def test_sample_test_data_fixture(
    sample_test_data: tuple[
        list[School], list[Course], list[Student], list[Enrollment]
    ],
):
    """
    Test that sample_test_data fixture returns a tuple of lists with expected types and content.
    """
    schools, courses, students, enrollments = sample_test_data
    assert isinstance(schools, list)
    assert isinstance(courses, list)
    assert isinstance(students, list)
    assert isinstance(enrollments, list)

    assert len(schools) > 0
    assert len(courses) > 0
    assert len(students) > 0
    assert len(enrollments) > 0

    assert isinstance(schools[0], School)
    assert isinstance(courses[0], Course)
    assert isinstance(students[0], Student)
    assert isinstance(enrollments[0], Enrollment)


@pytest.mark.models
def test_sample_schools_fixture(sample_schools: list[School]):
    """Test sample_schools fixture populates correctly."""
    assert isinstance(sample_schools, list)
    assert len(sample_schools) > 0
    assert all(isinstance(s, School) for s in sample_schools)


@pytest.mark.models
def test_sample_courses_fixture(sample_courses: list[Course]):
    """Test sample_courses fixture populates correctly."""
    assert isinstance(sample_courses, list)
    assert len(sample_courses) > 0
    assert all(isinstance(c, Course) for c in sample_courses)


@pytest.mark.models
def test_sample_students_fixture(sample_students: list[Student]):
    """Test sample_students fixture populates correctly."""
    assert isinstance(sample_students, list)
    assert len(sample_students) > 0
    assert all(isinstance(s, Student) for s in sample_students)


@pytest.mark.models
def test_sample_enrollments_fixture(sample_enrollments: list[Enrollment]):
    """Test sample_enrollments fixture populates correctly."""
    assert isinstance(sample_enrollments, list)
    assert len(sample_enrollments) > 0
    assert all(isinstance(e, Enrollment) for e in sample_enrollments)


@pytest.mark.models
def test_sample_school_fixture(sample_school: School):
    """Test sample_school fixture returns a single School instance."""
    assert isinstance(sample_school, School)
    assert sample_school.name == "Test University"
    assert sample_school.city == "San Francisco"


@pytest.mark.models
def test_sample_student_fixture(sample_student: Student):
    """Test sample_student fixture returns a single Student instance."""
    assert isinstance(sample_student, Student)
    assert sample_student.name == "John Doe"
    assert sample_student.major == "Computer Science"


@pytest.mark.fastapi
@pytest.mark.models
def test_test_fastapi_app_fixture(test_fastapi_app: FastAPI):
    """
    Test that the test_fastapi_app fixture returns a FastAPI instance
    and has the expected routes registered.
    """
    assert isinstance(test_fastapi_app, FastAPI)

    # Check for common routes
    routes = {route.path for route in test_fastapi_app.routes}
    assert "/" in routes
    assert "/health" in routes
    # Check for business routes
    assert "/schools/{school_id}" in routes
    assert "/schools" in routes
    assert "/students/{student_id}" in routes


@pytest.mark.fastapi
def test_test_client_fixture(test_client: TestClient):
    """
    Test that the test_client fixture returns a TestClient instance
    and can handle basic requests.
    """
    assert isinstance(test_client, TestClient)

    # Test a simple route
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "smarttemplates-test"}


@pytest.mark.templates
def test_template_context_fixture(template_context: dict[str, Any]):
    """Test that template_context fixture returns a dict with expected keys."""
    assert isinstance(template_context, dict)
    assert "title" in template_context
    assert "user" in template_context
    assert "items" in template_context
    assert "debug_mode" in template_context
    assert template_context["debug_mode"] is True


@pytest.mark.templates
def test_render_error_context_fixture(render_error_context: dict[str, Any]):
    """Test that render_error_context fixture returns a dict for error simulation."""
    assert isinstance(render_error_context, dict)
    assert "undefined_variable" in render_error_context
    assert "invalid_syntax" in render_error_context


@pytest.mark.templates
def test_assert_template_rendered_utility():
    """Test the assert_template_rendered utility function."""
    assert_template_rendered("Hello, {{ name }}!", ["Hello,", "{{ name }}!"])
    with pytest.raises(AssertionError, match="Expected 'Missing' not found"):
        assert_template_rendered("Hello World", ["Missing"])


@pytest.mark.templates
def test_assert_no_template_errors_utility():
    """Test the assert_no_template_errors utility function."""
    assert_no_template_errors(None)
    with pytest.raises(AssertionError, match="Unexpected template error"):
        assert_no_template_errors({"message": "Some error occurred"})


@pytest.mark.templates
def test_assert_template_error_utility():
    """
    Test the assert_template_error utility function using a mock error object.
    """

    # Create a mock object that mimics the expected error structure
    class MockErrorDetail:
        def __init__(self, error_type: str):
            self.error_type = error_type

    class MockTemplateError:
        def __init__(self, error_type: str):
            self.error = MockErrorDetail(error_type)

    mock_type_error = MockTemplateError("RenderTypeError")
    assert_template_error(mock_type_error, "RenderTypeError")

    with pytest.raises(
        AssertionError, match="Expected template error but none occurred"
    ):
        assert_template_error(None, "AnyError")

    with pytest.raises(
        AssertionError, match="Expected error type 'SyntaxError', got 'RenderTypeError'"
    ):
        assert_template_error(mock_type_error, "SyntaxError")

    # Test when the error object doesn't have the expected structure
    with pytest.raises(
        AssertionError, match="Error object does not have expected structure"
    ):
        assert_template_error("Just a string", "AnyError")

    with pytest.raises(
        AssertionError, match="Error object does not have expected structure"
    ):
        assert_template_error(object(), "AnyError")
