from tests import TEST_TEMPLATES_DIR
import pytest
from pathlib import Path

# Define the root directory for test templates relative to this test file
TEMPLATES_ROOT = Path(__file__).parent / "templates"

# List all expected template files relative to TEMPLATES_ROOT
# This list must be kept up-to-date with your project's template structure.
EXPECTED_TEMPLATE_FILES = [
    "base.html",
    "error.html",
    "school/dashboard.html",
    "school/list.html",
    "school/admin_dashboard.html",
    "course/detail.html",
    "course/instructor_view.html",
    "course/student_view.html",
    "student/profile.html",
    "student/transcript.html",
    "student/active.html",
    "student/completed.html",
    "student/reattempt.html",
    "enrollment/confirmation.html",
    "macros/student_components.html",
    "macros/course_components.html",
    "macros/navigation.html",
    "email/enrollment_confirmation.html",
    "email/course_completion.html",
]
@pytest.mark.parametrize("template_relative_path", EXPECTED_TEMPLATE_FILES)
def test_template_file_exists(template_relative_path):
    """
    Test to ensure that all specified HTML template files exist in the
    test fixtures directory.
    """
    template_full_path = TEMPLATES_ROOT / template_relative_path

    print(f"Checking for template: {template_full_path}") # For verbose output during tests

    assert template_full_path.exists(), \
        f"Missing template file: {template_full_path}"
    assert template_full_path.is_file(), \
        f"Path exists but is not a file: {template_full_path}"