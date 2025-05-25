"""
Test models package for SmartTemplates framework.

This package contains business object models used for testing template rendering,
object-based template resolution, and business scenario validation.

Business Model Hierarchy:
    School (1) → Course (N) → Student (N) → Enrollment (N)

The models use realistic relationships and provide comprehensive test data
for validating the SmartTemplates framework across different business scenarios.
"""

from .business_objects import (
    # Core Models
    School,
    Course,
    Student,
    Enrollment,
    # Enums
    EnrollmentStatus,
    CourseStatus,
    # Factory Functions
    create_sample_school,
    create_sample_course,
    create_sample_student,
    create_sample_enrollment,
    create_complete_test_data,
    # Utility Functions
    get_schools_with_courses,
    get_students_by_status,
    get_course_enrollment_summary,
)

__all__ = [
    # Core Models
    "School",
    "Course", 
    "Student",
    "Enrollment",
    # Enums
    "EnrollmentStatus",
    "CourseStatus",
    # Factory Functions
    "create_sample_school",
    "create_sample_course", 
    "create_sample_student",
    "create_sample_enrollment",
    "create_complete_test_data",
    # Utility Functions
    "get_schools_with_courses",
    "get_students_by_status",
    "get_course_enrollment_summary",
]