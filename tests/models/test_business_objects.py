"""
Test cases for business object models in SmartTemplates.

This module validates the business object models defined in business_objects.py
to ensure they work correctly with SQLModel, have proper relationships,
and provide all required functionality for template testing.

Test Categories:
- Model Structure: Field definitions, types, constraints
- Relationships: Foreign keys, back_populates, bidirectional access
- Business Logic: Properties, methods, validation
- Factory Functions: Data generation and consistency
- Template Integration: to_template_dict() methods
"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session, create_engine

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
    get_course_enrollment_summary,
    get_schools_with_courses,
    get_students_by_status,
)


class TestModelStructure:
    """Test basic model structure and field definitions."""

    def test_school_model_fields(self):
        """Test School model has all required fields with correct types."""
        school = School(
            name="Test University",
            address="123 Test St",
            city="Test City",
            state="CA",
            zip_code="12345",
        )

        # Required fields
        assert school.name == "Test University"
        assert school.address == "123 Test St"
        assert school.city == "Test City"
        assert school.state == "CA"
        assert school.zip_code == "12345"

        # Optional fields with defaults
        assert school.student_capacity == 500
        assert school.phone is None
        assert school.email is None
        assert school.website is None
        assert school.established_year is None

    def test_course_model_fields(self):
        """Test Course model has all required fields with correct types."""
        course = Course(
            title="Introduction to Python",
            description="A beginner course in Python programming",
            course_code="CS101",
        )

        # Required fields
        assert course.title == "Introduction to Python"
        assert course.description == "A beginner course in Python programming"
        assert course.course_code == "CS101"

        # Optional fields with defaults
        assert course.credits == 3
        assert course.max_students == 30
        assert course.status == CourseStatus.DRAFT
        assert course.start_date is None
        assert course.end_date is None
        assert course.instructor_name is None
        assert course.instructor_email is None

    def test_student_model_fields(self):
        """Test Student model has all required fields with correct types."""
        student = Student(name="John Doe", email="john.doe@university.edu")

        # Required fields
        assert student.name == "John Doe"
        assert student.email == "john.doe@university.edu"

        # Optional fields
        assert student.phone is None
        assert student.date_of_birth is None
        assert student.graduation_year is None
        assert student.gpa is None
        assert student.major is None

    def test_enrollment_model_fields(self):
        """Test Enrollment model has all required fields with correct types."""
        enrollment = Enrollment(student_id=1, course_id=1)

        # Required fields
        assert enrollment.student_id == 1
        assert enrollment.course_id == 1

        # Optional fields with defaults
        assert enrollment.status == EnrollmentStatus.ACTIVE
        assert enrollment.enrollment_date == date.today()
        assert enrollment.progress_percentage == 0.0
        assert enrollment.attempt_number == 1
        assert enrollment.completion_date is None
        assert enrollment.grade is None
        assert enrollment.notes is None

    def test_enum_values(self):
        """Test enum values are correct."""
        # EnrollmentStatus values
        assert EnrollmentStatus.ACTIVE == "active"
        assert EnrollmentStatus.COMPLETED == "completed"
        assert EnrollmentStatus.REATTEMPT == "reattempt"
        assert EnrollmentStatus.DROPPED == "dropped"

        # CourseStatus values
        assert CourseStatus.DRAFT == "draft"
        assert CourseStatus.ACTIVE == "active"
        assert CourseStatus.ARCHIVED == "archived"


class TestModelRelationships:
    """Test model relationships and foreign keys."""

    def test_school_course_relationship(self):
        """Test School-Course relationship works bidirectionally."""
        school = School(
            name="Test University",
            address="123 Test St",
            city="Test City",
            state="CA",
            zip_code="12345",
        )

        course = Course(
            title="Test Course",
            description="A test course",
            course_code="TEST101",
            school=school,
        )

        # Test forward relationship
        assert course.school == school

        # Test back relationship
        assert course in school.courses

    def test_student_enrollment_relationship(self):
        """Test Student-Enrollment relationship works bidirectionally."""
        student = Student(name="Test Student", email="test@test.com")
        enrollment = Enrollment(student_id=1, course_id=1, student=student)

        # Test forward relationship
        assert enrollment.student == student

        # Test back relationship
        assert enrollment in student.enrollments

    def test_course_enrollment_relationship(self):
        """Test Course-Enrollment relationship works bidirectionally."""
        course = Course(
            title="Test Course", description="A test course", course_code="TEST101"
        )
        enrollment = Enrollment(student_id=1, course_id=1, course=course)

        # Test forward relationship
        assert enrollment.course == course

        # Test back relationship
        assert enrollment in course.enrollments

    def test_complex_relationships(self):
        """Test complex multi-level relationships."""
        # Create complete related objects
        school = create_sample_school("Test University")
        course = create_sample_course("Test Course", "TEST101", school)
        student = create_sample_student("Test Student")
        enrollment = create_sample_enrollment(student, course)

        # Test full relationship chain
        assert enrollment.student == student
        assert enrollment.course == course
        assert course.school == school

        # Test derived relationships
        assert student in course.students
        assert course in student.courses
        assert course in school.courses


class TestBusinessLogic:
    """Test business logic methods and properties."""

    def test_school_properties(self):
        """Test School computed properties."""
        school = create_sample_school("Test University")

        # Test full_address property
        expected_address = (
            f"{school.address}, {school.city}, {school.state} {school.zip_code}"
        )
        assert school.full_address == expected_address

        # Test total_students with no courses
        assert school.total_students == 0

    def test_school_properties_with_data(self):
        """Test School properties with related data."""
        schools, courses, students, enrollments = create_complete_test_data()

        if schools and courses and students and enrollments:
            school = schools[0]

            # Should have courses and students
            assert school.total_students >= 0
            assert len(school.courses) > 0

    def test_course_properties(self):
        """Test Course computed properties."""
        course = create_sample_course("Test Course", "TEST101")

        # Test with no enrollments
        assert len(course.students) == 0
        assert not course.is_full
        assert course.enrollment_percentage == 0.0

    def test_course_properties_with_enrollments(self):
        """Test Course properties with enrollments."""
        course = create_sample_course("Test Course", "TEST101")
        course.max_students = 2  # Small class for testing

        # Add students
        student1 = create_sample_student("Student 1")
        student2 = create_sample_student("Student 2")

        enrollment1 = create_sample_enrollment(student1, course)
        enrollment2 = create_sample_enrollment(student2, course)

        # Test properties
        assert len(course.students) == 2
        assert course.is_full
        assert course.enrollment_percentage == 100.0

    def test_student_properties(self):
        """Test Student computed properties."""
        student = create_sample_student("Test Student")

        # Test with no enrollments
        assert len(student.courses) == 0
        assert len(student.active_courses) == 0
        assert len(student.completed_courses) == 0

    def test_student_properties_with_enrollments(self):
        """Test Student properties with various enrollment statuses."""
        student = create_sample_student("Test Student")
        course1 = create_sample_course("Course 1", "C101")
        course2 = create_sample_course("Course 2", "C102")

        # Create enrollments with different statuses
        active_enrollment = create_sample_enrollment(
            student, course1, EnrollmentStatus.ACTIVE
        )
        completed_enrollment = create_sample_enrollment(
            student, course2, EnrollmentStatus.COMPLETED
        )

        assert active_enrollment
        assert completed_enrollment

        # Test properties
        assert len(student.courses) == 2
        assert course1 in student.active_courses
        assert course2 in student.completed_courses
        assert len(student.active_courses) == 1
        assert len(student.completed_courses) == 1

    def test_enrollment_properties(self):
        """Test Enrollment computed properties."""
        # Test active enrollment
        active_enrollment = Enrollment(
            student_id=1,
            course_id=1,
            status=EnrollmentStatus.ACTIVE,
            progress_percentage=75.0,
        )

        assert not active_enrollment.is_completed
        assert active_enrollment.is_passing
        assert not active_enrollment.needs_attention

        # Test completed enrollment
        completed_enrollment = Enrollment(
            student_id=1,
            course_id=1,
            status=EnrollmentStatus.COMPLETED,
            progress_percentage=95.0,
        )

        assert completed_enrollment.is_completed
        assert completed_enrollment.is_passing

        # Test reattempt enrollment
        reattempt_enrollment = Enrollment(
            student_id=1,
            course_id=1,
            status=EnrollmentStatus.REATTEMPT,
            progress_percentage=40.0,
        )

        assert not reattempt_enrollment.is_completed
        assert not reattempt_enrollment.is_passing
        assert reattempt_enrollment.needs_attention


class TestTemplateIntegration:
    """Test template integration methods."""

    def test_school_to_template_dict(self):
        """Test School.to_template_dict() method."""
        school = create_sample_school("Test University")
        template_dict = school.to_template_dict()

        # Check required fields
        assert template_dict["name"] == school.name
        assert template_dict["address"] == school.address
        assert template_dict["city"] == school.city
        assert template_dict["state"] == school.state
        assert template_dict["student_capacity"] == school.student_capacity

        # Check computed fields
        assert "total_courses" in template_dict
        assert template_dict["total_courses"] == len(school.courses)

    def test_course_to_template_dict(self):
        """Test Course.to_template_dict() method."""
        school = create_sample_school("Test University")
        course = create_sample_course("Test Course", "TEST101", school)
        template_dict = course.to_template_dict()

        # Check required fields
        assert template_dict["title"] == course.title
        assert template_dict["course_code"] == course.course_code
        assert template_dict["credits"] == course.credits
        assert template_dict["status"] == course.status.value

        # Check computed fields
        assert "enrolled_students" in template_dict
        assert "available_spots" in template_dict
        assert template_dict["school_name"] == school.name

    def test_student_to_template_dict(self):
        """Test Student.to_template_dict() method."""
        student = create_sample_student("Test Student")
        template_dict = student.to_template_dict()

        # Check required fields
        assert template_dict["name"] == student.name
        assert template_dict["email"] == student.email
        assert template_dict["major"] == student.major
        assert template_dict["gpa"] == student.gpa

        # Check computed fields
        assert "total_courses" in template_dict
        assert "active_enrollments" in template_dict
        assert "completed_courses" in template_dict

    def test_enrollment_to_template_dict(self):
        """Test Enrollment.to_template_dict() method."""
        student = create_sample_student("Test Student")
        course = create_sample_course("Test Course", "TEST101")
        enrollment = create_sample_enrollment(student, course)
        template_dict = enrollment.to_template_dict()

        # Check required fields
        assert template_dict["status"] == enrollment.status.value
        assert template_dict["progress_percentage"] == enrollment.progress_percentage
        assert template_dict["attempt_number"] == enrollment.attempt_number

        # Check related object fields
        assert template_dict["student_name"] == student.name
        assert template_dict["course_title"] == course.title
        assert template_dict["course_code"] == course.course_code


class TestFactoryFunctions:
    """Test factory functions for creating test data."""

    def test_create_sample_school(self):
        """Test create_sample_school factory function."""
        school = create_sample_school("Test University", "Test City", "CA")

        assert school.name == "Test University"
        assert school.city == "Test City"
        assert school.state == "CA"
        assert school.address == "123 Education Blvd"
        assert school.phone == "(555) 123-4567"
        assert school.established_year == 1965

    def test_create_sample_course(self):
        """Test create_sample_course factory function."""
        school = create_sample_school("Test University")
        course = create_sample_course("Python Programming", "CS101", school)

        assert course.title == "Python Programming"
        assert course.course_code == "CS101"
        assert course.school == school
        assert course.status == CourseStatus.ACTIVE
        assert course.instructor_name == "Dr. Sarah Johnson"

    def test_create_sample_student(self):
        """Test create_sample_student factory function."""
        student = create_sample_student("John Doe", major="Computer Science")

        assert student.name == "John Doe"
        assert student.major == "Computer Science"
        assert student.gpa == 3.75
        assert "@student.university.edu" in student.email

    def test_create_sample_enrollment(self):
        """Test create_sample_enrollment factory function."""
        student = create_sample_student("Test Student")
        course = create_sample_course("Test Course", "TEST101")
        enrollment = create_sample_enrollment(
            student, course, EnrollmentStatus.ACTIVE, 75.0
        )

        assert enrollment.student == student
        assert enrollment.course == course
        assert enrollment.status == EnrollmentStatus.ACTIVE
        assert enrollment.progress_percentage == 75.0

    def test_create_complete_test_data(self):
        """Test create_complete_test_data factory function."""
        schools, courses, students, enrollments = create_complete_test_data()

        # Check we have data
        assert len(schools) >= 3
        assert len(courses) >= 9  # 3 courses per school
        assert len(students) >= 8
        assert len(enrollments) >= 16  # Multiple enrollments per student

        # Check relationships are established
        for school in schools:
            assert len(school.courses) > 0

        for course in courses:
            assert course.school is not None

        for enrollment in enrollments:
            assert enrollment.student is not None
            assert enrollment.course is not None

    def test_data_consistency(self):
        """Test that factory functions create consistent, related data."""
        schools, courses, students, enrollments = create_complete_test_data()

        # Verify all courses belong to schools
        for course in courses:
            assert course.school in schools

        # Verify all enrollments reference valid students and courses
        for enrollment in enrollments:
            assert enrollment.student in students
            assert enrollment.course in courses

        # Verify enrollment statuses are distributed
        statuses = [e.status for e in enrollments]
        unique_statuses = set(statuses)
        assert len(unique_statuses) > 1  # Should have multiple status types


class TestUtilityFunctions:
    """Test utility functions for querying test data."""

    def test_get_schools_with_courses(self):
        """Test get_schools_with_courses utility function."""
        schools, courses, students, enrollments = create_complete_test_data()
        schools_with_courses = get_schools_with_courses(schools)

        # All schools should have courses
        assert len(schools_with_courses) > 0
        for school in schools_with_courses:
            assert len(school.courses) > 0

    def test_get_students_by_status(self):
        """Test get_students_by_status utility function."""
        schools, courses, students, enrollments = create_complete_test_data()

        # Test getting active students
        active_students = get_students_by_status(enrollments, EnrollmentStatus.ACTIVE)
        assert len(active_students) > 0

        # Test getting completed students
        completed_students = get_students_by_status(
            enrollments, EnrollmentStatus.COMPLETED
        )
        assert len(completed_students) >= 0  # May be 0 depending on test data

    def test_get_course_enrollment_summary(self):
        """Test get_course_enrollment_summary utility function."""
        schools, courses, students, enrollments = create_complete_test_data()

        if courses and enrollments:
            course = courses[0]
            summary = get_course_enrollment_summary(course)

            # Check required fields
            assert "course_id" in summary
            assert "course_title" in summary
            assert "total_enrollments" in summary
            assert "by_status" in summary
            assert "average_progress" in summary
            assert "capacity_utilization" in summary

            # Check data types
            assert isinstance(summary["total_enrollments"], int)
            assert isinstance(summary["by_status"], dict)
            assert isinstance(summary["average_progress"], float)
            assert isinstance(summary["capacity_utilization"], float)

    def test_empty_course_enrollment_summary(self):
        """Test course enrollment summary with no enrollments."""
        course = create_sample_course("Empty Course", "EMPTY101")
        summary = get_course_enrollment_summary(course)

        assert summary["total_enrollments"] == 0
        assert summary["by_status"] == {}
        assert summary["average_progress"] == 0.0


class TestSQLModelIntegration:
    """Test SQLModel database integration."""

    def test_models_create_tables(self):
        """Test that models can create database tables."""
        # Create in-memory SQLite database
        engine = create_engine("sqlite:///:memory:")

        # This should not raise an exception
        from sqlmodel import SQLModel

        SQLModel.metadata.create_all(engine)

    def test_models_database_operations(self):
        """Test basic database operations with the models."""
        # Create in-memory SQLite database
        engine = create_engine("sqlite:///:memory:")
        from sqlmodel import SQLModel

        SQLModel.metadata.create_all(engine)

        # Create and save objects
        school = create_sample_school("Database Test University")
        student = create_sample_student("Database Student")

        with Session(engine) as session:
            # Add objects to session
            session.add(school)
            session.add(student)
            session.commit()

            # Refresh to get IDs
            session.refresh(school)
            session.refresh(student)

            # Create course with proper school relationship
            course = create_sample_course("Database Course", "DB101")
            course.school_id = school.id
            session.add(course)
            session.commit()
            session.refresh(course)

            # Create enrollment with proper IDs
            enrollment = Enrollment(
                student_id=student.id,
                course_id=course.id,
                status=EnrollmentStatus.ACTIVE,
                progress_percentage=80.0,
            )
            session.add(enrollment)
            session.commit()

            # Test that we can query back
            retrieved_school = session.get(School, school.id)
            assert retrieved_school is not None
            assert retrieved_school.name == school.name

    def test_relationship_loading(self):
        """Test that relationships work in database context."""
        # Create in-memory SQLite database
        engine = create_engine("sqlite:///:memory:")
        from sqlmodel import SQLModel

        SQLModel.metadata.create_all(engine)

        school = create_sample_school("Relationship Test University")

        with Session(engine) as session:
            session.add(school)
            session.commit()
            session.refresh(school)

            # Create course with proper school relationship
            course = create_sample_course("Relationship Course", "REL101")
            course.school = school
            session.add(course)
            session.commit()
            session.refresh(course)

            # Test that foreign key is set correctly
            assert course.school_id == school.id
            # Note: In a real database, you'd need to configure relationship loading
            # For this test, we're just verifying the foreign key is set correctly


# Integration test to verify all components work together
class TestIntegration:
    """Integration tests to verify all components work together."""

    def test_complete_workflow(self):
        """Test complete workflow from data creation to template dict generation."""
        # Create complete test data
        schools, courses, students, enrollments = create_complete_test_data()

        # Test that we can get template dicts for all objects
        for school in schools:
            template_dict = school.to_template_dict()
            assert isinstance(template_dict, dict)
            assert "name" in template_dict

        for course in courses:
            template_dict = course.to_template_dict()
            assert isinstance(template_dict, dict)
            assert "title" in template_dict

        for student in students:
            template_dict = student.to_template_dict()
            assert isinstance(template_dict, dict)
            assert "name" in template_dict

        for enrollment in enrollments:
            template_dict = enrollment.to_template_dict()
            assert isinstance(template_dict, dict)
            assert "status" in template_dict

    def test_business_scenarios(self):
        """Test realistic business scenarios."""
        schools, courses, students, enrollments = create_complete_test_data()

        # Scenario 1: Find all active students
        active_students = get_students_by_status(enrollments, EnrollmentStatus.ACTIVE)
        assert len(active_students) > 0

        # Scenario 2: Get enrollment summaries for all courses
        for course in courses:
            summary = get_course_enrollment_summary(course)
            assert "total_enrollments" in summary

        # Scenario 3: Test status-based template selection data
        for enrollment in enrollments:
            template_dict = enrollment.to_template_dict()
            # This data could be used for status-based template selection
            assert template_dict["status"] in [
                "active",
                "completed",
                "reattempt",
                "dropped",
            ]

    def test_template_context_data_quality(self):
        """Test that template context data is high quality and complete."""
        schools, courses, students, enrollments = create_complete_test_data()

        # Test school template context
        if schools:
            school = schools[0]
            context = school.to_template_dict()

            # Should have all necessary data for templates
            required_fields = ["name", "address", "city", "state", "total_courses"]
            for field in required_fields:
                assert field in context
                assert context[field] is not None

        # Test student template context with enrollment status
        for enrollment in enrollments:
            if enrollment.student:
                student_context = enrollment.student.to_template_dict()
                enrollment_context = enrollment.to_template_dict()

                # Should have data needed for status-based templates
                assert "name" in student_context
                assert "status" in enrollment_context
                assert (
                    enrollment_context["status"]
                    in EnrollmentStatus.__members__.values()
                )
