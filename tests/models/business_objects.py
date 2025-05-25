"""
Business object models for SmartTemplates testing.

This module defines SQLModel objects with realistic relationships for testing
template rendering, object-based resolution, and business scenario validation.

Business Model Hierarchy:
    School (1) → Course (N) → Student (N) → Enrollment (N)

Key Features:
- Realistic business relationships and data
- Support for status-based template selection
- Factory functions for test data generation
- Multi-level object hierarchy for complex template testing
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, List

from sqlmodel import Field, Relationship, SQLModel


# Enums for business logic
class EnrollmentStatus(str, Enum):
    """Student enrollment status for template selection."""
    ACTIVE = "active"
    COMPLETED = "completed" 
    REATTEMPT = "reattempt"
    DROPPED = "dropped"


class CourseStatus(str, Enum):
    """Course availability status."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


# Core Business Models
class School(SQLModel, table=True):
    """School model with courses relationship."""
    
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    address: str
    city: str
    state: str
    zip_code: str
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    established_year: int | None = None
    student_capacity: int = Field(default=500)
    
    # Relationships
    # This list will be populated automatically by SQLModel when loading from DB
    # or needs manual appending in factory functions if building in-memory graphs.
    courses: List["Course"] = Relationship(back_populates="school")
    
    def to_template_dict(self) -> dict[str, Any]:
        """Convert to template-friendly dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "phone": self.phone,
            "email": self.email,
            "website": self.website,
            "established_year": self.established_year,
            "student_capacity": self.student_capacity,
            # 'courses' relationship should be populated for this to work in memory
            "total_courses": len(self.courses) if self.courses else 0,
        }
    
    @property
    def full_address(self) -> str:
        """Complete address for display."""
        return f"{self.address}, {self.city}, {self.state} {self.zip_code}"
    
    @property
    def total_students(self) -> int:
        """Total enrolled students across all courses."""
        if not self.courses:
            return 0
        # 'courses' relationship should be populated for this to work in memory
        # 'course.students' property also relies on 'enrollments' being populated
        return sum(len(course.students) for course in self.courses)


class Course(SQLModel, table=True):
    """Course model with school and student relationships."""
    
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    description: str
    course_code: str = Field(unique=True, index=True)
    credits: int = Field(default=3)
    max_students: int = Field(default=30)
    status: CourseStatus = Field(default=CourseStatus.DRAFT)
    start_date: date | None = None
    end_date: date | None = None
    instructor_name: str | None = None
    instructor_email: str | None = None
    
    # Foreign Keys
    school_id: int | None = Field(default=None, foreign_key="school.id")
    
    # Relationships
    school: School | None = Relationship(back_populates="courses")
    # This list needs manual appending in factory functions for in-memory graphs
    enrollments: List["Enrollment"] = Relationship(back_populates="course")
    
    @property
    def students(self) -> List["Student"]:
        """Get all students enrolled in this course."""
        if not self.enrollments:
            return []
        # 'enrollments' relationship should be populated for this to work in memory
        return [enrollment.student for enrollment in self.enrollments if enrollment.student]
    
    def to_template_dict(self) -> dict[str, Any]:
        """Convert to template-friendly dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "course_code": self.course_code,
            "credits": self.credits,
            "max_students": self.max_students,
            "status": self.status.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "instructor_name": self.instructor_name,
            "instructor_email": self.instructor_email,
            "school_name": self.school.name if self.school else None,
            # 'students' property relies on 'enrollments' being populated
            "enrolled_students": len(self.students),
            "available_spots": self.max_students - len(self.students),
        }
    
    @property
    def is_full(self) -> bool:
        """Check if course is at capacity."""
        # 'students' property relies on 'enrollments' being populated
        return len(self.students) >= self.max_students
    
    @property
    def enrollment_percentage(self) -> float:
        """Calculate enrollment percentage."""
        if self.max_students == 0:
            return 0.0
        # 'students' property relies on 'enrollments' being populated
        return (len(self.students) / self.max_students) * 100


class Student(SQLModel, table=True):
    """Student model with enrollment relationships."""
    
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(unique=True, index=True)
    phone: str | None = None
    date_of_birth: date | None = None
    graduation_year: int | None = None
    gpa: float | None = Field(default=None, ge=0.0, le=4.0)
    major: str | None = None
    address: str | None = None
    emergency_contact: str | None = None
    emergency_phone: str | None = None
    
    # Relationships
    # This list needs manual appending in factory functions for in-memory graphs
    enrollments: List["Enrollment"] = Relationship(back_populates="student")
    
    @property
    def courses(self) -> List[Course]:
        """Get all courses this student is enrolled in."""
        if not self.enrollments:
            return []
        # 'enrollments' relationship should be populated for this to work in memory
        return [enrollment.course for enrollment in self.enrollments if enrollment.course]
    
    def to_template_dict(self) -> dict[str, Any]:
        """Convert to template-friendly dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "graduation_year": self.graduation_year,
            "gpa": self.gpa,
            "major": self.major,
            "address": self.address,
            "emergency_contact": self.emergency_contact,
            "emergency_phone": self.emergency_phone,
            # 'courses' property relies on 'enrollments' being populated
            "total_courses": len(self.courses),
            # 'enrollments' relationship should be populated
            "active_enrollments": len([e for e in self.enrollments if e.status == EnrollmentStatus.ACTIVE]),
            "completed_courses": len([e for e in self.enrollments if e.status == EnrollmentStatus.COMPLETED]),
        }
    
    @property
    def active_courses(self) -> List[Course]:
        """Get courses with active enrollment."""
        return [
            enrollment.course 
            for enrollment in self.enrollments 
            if enrollment.status == EnrollmentStatus.ACTIVE and enrollment.course
        ]
    
    @property
    def completed_courses(self) -> List[Course]:
        """Get courses with completed enrollment."""
        return [
            enrollment.course
            for enrollment in self.enrollments
            if enrollment.status == EnrollmentStatus.COMPLETED and enrollment.course
        ]


class Enrollment(SQLModel, table=True):
    """Enrollment relationship between students and courses."""
    
    id: int | None = Field(default=None, primary_key=True)
    # student_id and course_id are required fields
    student_id: int = Field(foreign_key="student.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    
    status: EnrollmentStatus = Field(default=EnrollmentStatus.ACTIVE, index=True)
    enrollment_date: date = Field(default_factory=lambda: date.today())
    completion_date: date | None = None
    grade: str | None = None
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    notes: str | None = None
    attempt_number: int = Field(default=1, ge=1)
    
    # Relationships
    # FIX: Changed `Student | None` to `Student` and `Course | None` to `Course`
    # because `student_id` and `course_id` are non-nullable.
    student: Student = Relationship(back_populates="enrollments")
    course: Course = Relationship(back_populates="enrollments")
    
    def to_template_dict(self) -> dict[str, Any]:
        """Convert to template-friendly dictionary."""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "course_id": self.course_id,
            "status": self.status.value,
            "enrollment_date": self.enrollment_date.isoformat(),
            "completion_date": self.completion_date.isoformat() if self.completion_date else None,
            "grade": self.grade,
            "progress_percentage": self.progress_percentage,
            "notes": self.notes,
            "attempt_number": self.attempt_number,
            "student_name": self.student.name, # No 'if self.student' needed due to non-nullable type
            "course_title": self.course.title, # No 'if self.course' needed due to non-nullable type
            "course_code": self.course.course_code, # No 'if self.course' needed due to non-nullable type
        }
    
    @property
    def is_completed(self) -> bool:
        """Check if enrollment is completed."""
        return self.status == EnrollmentStatus.COMPLETED
    
    @property
    def is_passing(self) -> bool:
        """Check if student is passing (based on progress)."""
        return self.progress_percentage >= 60.0
    
    @property
    def needs_attention(self) -> bool:
        """Check if enrollment needs attention."""
        return (
            self.status == EnrollmentStatus.REATTEMPT or
            (self.status == EnrollmentStatus.ACTIVE and self.progress_percentage < 50.0)
        )


# Factory Functions for Test Data
def create_sample_school(
    name: str = "Tech University",
    city: str = "San Francisco",
    state: str = "CA",
) -> School:
    """Create a sample school with realistic data."""
    return School(
        name=name,
        address="123 Education Blvd",
        city=city,
        state=state,
        zip_code="94105",
        phone="(555) 123-4567",
        email=f"info@{name.lower().replace(' ', '')}.edu",
        website=f"https://www.{name.lower().replace(' ', '')}.edu",
        established_year=1965,
        student_capacity=2500,
    )


def create_sample_course(
    title: str = "Introduction to Python",
    course_code: str = "CS101",
    school: School | None = None,
) -> Course:
    """Create a sample course with realistic data."""
    return Course(
        title=title,
        description=f"An introductory course covering {title.lower()} fundamentals and practical applications.",
        course_code=course_code,
        credits=3,
        max_students=25,
        status=CourseStatus.ACTIVE,
        start_date=date(2024, 9, 1),
        end_date=date(2024, 12, 15),
        instructor_name="Dr. Sarah Johnson",
        instructor_email="s.johnson@university.edu",
        school=school, # This links the Course to the School object
    )


def create_sample_student(
    name: str = "John Doe",
    email: str | None = None,
    major: str = "Computer Science",
) -> Student:
    """Create a sample student with realistic data."""
    if email is None:
        email = f"{name.lower().replace(' ', '.')}@student.university.edu"
    
    return Student(
        name=name,
        email=email,
        phone="(555) 987-6543",
        date_of_birth=date(2000, 5, 15),
        graduation_year=2024,
        gpa=3.75,
        major=major,
        address="456 Student Drive, Apt 12B",
        emergency_contact="Jane Doe",
        emergency_phone="(555) 555-0123",
    )


def create_sample_enrollment(
    student: Student,
    course: Course,
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE,
    progress: float = 75.0,
) -> Enrollment:
    """Create a sample enrollment with realistic data."""
    enrollment = Enrollment(
        student=student, # This links the Enrollment to the Student object
        course=course,   # This links the Enrollment to the Course object
        status=status,
        enrollment_date=date(2024, 8, 25),
        progress_percentage=progress,
        attempt_number=1,
    )
    
    # Set completion data for completed enrollments
    if status == EnrollmentStatus.COMPLETED:
        enrollment.completion_date = date(2024, 12, 15)
        enrollment.grade = "A-" if progress >= 90 else "B+" if progress >= 80 else "B"
        enrollment.progress_percentage = 100.0
    
    return enrollment


def create_complete_test_data() -> tuple[List[School], List[Course], List[Student], List[Enrollment]]:
    """Create comprehensive test data with relationships."""
    
    # Create schools
    schools = [
        create_sample_school("Tech University", "San Francisco", "CA"),
        create_sample_school("State College", "Austin", "TX"),
        create_sample_school("Community College", "Portland", "OR"),
    ]
    
    # Create courses for each school
    courses = []
    course_name_data = [
        ("Introduction to Python", "CS101"),
        ("Web Development", "CS102"),
        ("Database Design", "CS201"),
        ("Machine Learning", "CS301"), # Not all will be used
        ("Software Engineering", "CS302"), # Not all will be used
    ]
    
    for i, school in enumerate(schools):
        school_suffix = str(i + 1) # A simple way to get a unique suffix per school
        for j, (title, base_code) in enumerate(course_name_data[:3]): # 3 courses per school
            # FIX: Changed course_code generation for uniqueness across schools
            course_code = f"{base_code}-{school_suffix}-{j+1}" 
            course = create_sample_course(title, course_code, school)
            courses.append(course)
            # FIX: Manually append course to school's courses list for in-memory graph
            school.courses.append(course)
    
    # Create students
    student_data = [
        ("Alice Johnson", "Computer Science"),
        ("Bob Smith", "Information Systems"),
        ("Carol Davis", "Web Development"),
        ("David Wilson", "Computer Science"),
        ("Emma Brown", "Data Science"),
        ("Frank Miller", "Computer Science"),
        ("Grace Lee", "Information Systems"),
        ("Henry Taylor", "Web Development"),
    ]
    
    students = []
    for name, major in student_data:
        student = create_sample_student(name, major=major)
        students.append(student)
    
    # Create enrollments (realistic distribution)
    enrollments = []
    enrollment_scenarios = [
        (EnrollmentStatus.ACTIVE, 75.0),
        (EnrollmentStatus.COMPLETED, 95.0),
        (EnrollmentStatus.ACTIVE, 60.0),
        (EnrollmentStatus.REATTEMPT, 40.0),
        (EnrollmentStatus.COMPLETED, 88.0),
        (EnrollmentStatus.ACTIVE, 85.0),
        (EnrollmentStatus.DROPPED, 25.0),
        (EnrollmentStatus.ACTIVE, 70.0),
    ]
    
    # Enroll students in courses (multiple enrollments per student)
    course_index = 0
    for i, student in enumerate(students):
        # Each student enrolls in 2-3 courses, cycling through available courses
        num_courses_to_enroll = 2 if i % 3 == 0 else 3
        
        for j in range(num_courses_to_enroll):
            if course_index >= len(courses):
                course_index = 0 # Cycle back to the start of courses if we run out
            
            course = courses[course_index]
            
            # Use a scenario from the list, cycle if needed
            scenario_idx = (i * num_courses_to_enroll + j) % len(enrollment_scenarios)
            status, progress = enrollment_scenarios[scenario_idx]
            
            enrollment = create_sample_enrollment(student, course, status, progress)
            enrollments.append(enrollment)
            
            # FIX: Manually append enrollment to both student's and course's enrollment lists
            student.enrollments.append(enrollment)
            course.enrollments.append(enrollment)
            
            course_index += 1 # Move to the next course for the next enrollment
    
    return schools, courses, students, enrollments


# Utility Functions for Test Queries
def get_schools_with_courses(schools: List[School]) -> List[School]:
    """Get schools that have courses."""
    # This relies on school.courses being populated, which the updated factory does.
    return [school for school in schools if school.courses]


def get_students_by_status(
    enrollments: List[Enrollment], 
    status: EnrollmentStatus
) -> List[Student]:
    """Get students by enrollment status."""
    students = []
    for enrollment in enrollments:
        # No 'if enrollment.student' check needed due to non-nullable type hint
        if enrollment.status == status:
            students.append(enrollment.student)
    return list(students)


def get_course_enrollment_summary(course: Course) -> dict[str, Any]:
    """Get enrollment summary for a course."""
    # This relies on course.enrollments being populated, which the updated factory does.
    if not course.enrollments:
        return {
            "course_id": course.id,
            "course_title": course.title,
            "total_enrollments": 0,
            "by_status": {},
            "average_progress": 0.0,
        }
    
    by_status = {}
    total_progress = 0.0
    
    for enrollment in course.enrollments:
        status = enrollment.status.value
        by_status[status] = by_status.get(status, 0) + 1
        total_progress += enrollment.progress_percentage
    
    return {
        "course_id": course.id,
        "course_title": course.title,
        "total_enrollments": len(course.enrollments),
        "by_status": by_status,
        "average_progress": total_progress / len(course.enrollments),
        "capacity_utilization": (len(course.enrollments) / course.max_students) * 100,
    }
