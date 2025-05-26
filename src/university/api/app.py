"""
Test FastAPI application for comprehensive integration testing.

This application demonstrates real-world usage patterns and provides
endpoints for testing all SmartTemplates FastAPI features.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from smart_templates.fastapi_integration import SmartFastApiTemplates, create_smart_response
from university.models.business_objects import (
    Course,
    EnrollmentStatus,
    School,
    Student,
    create_complete_test_data,
    create_sample_course,
    create_sample_school,
    create_sample_student,
)

# Initialize templates
templates = SmartFastApiTemplates(
    "tests/fixtures/templates",
    debug_mode=True,
    api_path_prefix="/api/"
)

# Register business object templates
templates.registry.register_simple(School, template_name="school/dashboard.html")
templates.registry.register_simple(School, template_name="school/list.html", variation="list")
templates.registry.register_simple(Student, template_name="student/profile.html")
templates.registry.register_simple(
    Student, 
    template_name="student/active.html", 
    variation=EnrollmentStatus.ACTIVE
)
templates.registry.register_simple(
    Student, 
    template_name="student/completed.html", 
    variation=EnrollmentStatus.COMPLETED
)
templates.registry.register_simple(Course, template_name="course/detail.html")
templates.registry.register_simple(
    Course, 
    template_name="course/instructor_view.html", 
    variation="instructor"
)

# Create decorator
smart_response = create_smart_response(templates)

# Initialize app
app = FastAPI(title="SmartTemplates Test API", version="1.0.0")

# Sample data
schools, courses, students, enrollments = create_complete_test_data()

# Assign IDs to objects for testing
for i, school in enumerate(schools, 1):
    school.id = i

for i, course in enumerate(courses, 1):
    course.id = i

for i, student in enumerate(students, 1):
    student.id = i

for i, enrollment in enumerate(enrollments, 1):
    enrollment.id = i


@app.get("/")
async def root():
    return {"message": "SmartTemplates Test API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "smarttemplates-test"}


# School routes
@app.get("/schools")
@smart_response("school/list.html")
async def list_schools(request: Request):
    """List all schools - returns HTML or JSON based on Accept header."""
    return {"schools": schools}


@app.get("/schools/{school_id}")
@smart_response("school/dashboard.html")
async def get_school(request: Request, school_id: int):
    """Get school by ID - demonstrates object-based template resolution."""
    school = next((s for s in schools if s.id == school_id), None)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school


@app.get("/schools/{school_id}/admin")
@smart_response("school/admin_dashboard.html")
async def get_school_admin(request: Request, school_id: int):
    """School admin dashboard - demonstrates template variations."""
    school = next((s for s in schools if s.id == school_id), None)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school


# Student routes
@app.get("/students")
async def list_students(request: Request):
    """List all students - JSON only endpoint."""
    return {"students": [s.to_template_dict() for s in students]}


@app.get("/students/{student_id}")
@smart_response("student/profile.html")
async def get_student(request: Request, student_id: int):
    """Get student by ID - demonstrates status-based template variations."""
    student = next((s for s in students if s.id == student_id), None)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@app.get("/students/{student_id}/active")
@smart_response("student/active.html")
async def get_student_active_status(request: Request, student_id: int):
    """Student active status view - demonstrates enrollment status templates."""
    student = next((s for s in students if s.id == student_id), None)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Use variation to select active template
    content, error = templates.render_obj(
        student, 
        {"request": request},
        variation=EnrollmentStatus.ACTIVE
    )
    
    if error:
        raise HTTPException(status_code=500, detail="Template error")
    
    return HTMLResponse(content=content)


@app.get("/students/{student_id}/completed")
@smart_response("student/completed.html")
async def get_student_completed_status(request: Request, student_id: int):
    """Student completed status view - demonstrates enrollment status templates."""
    student = next((s for s in students if s.id == student_id), None)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Use variation to select completed template
    content, error = templates.render_obj(
        student, 
        {"request": request},
        variation=EnrollmentStatus.COMPLETED
    )
    
    if error:
        raise HTTPException(status_code=500, detail="Template error")
    
    return HTMLResponse(content=content)


# Course routes
@app.get("/courses/{course_id}")
@smart_response("course/detail.html")
async def get_course(request: Request, course_id: int):
    """Get course by ID - demonstrates instructor/student view variations."""
    course = next((c for c in courses if c.id == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@app.get("/courses/{course_id}/instructor")
@smart_response("course/instructor_view.html")
async def get_course_instructor_view(request: Request, course_id: int):
    """Instructor view of course - demonstrates template variations."""
    course = next((c for c in courses if c.id == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Use variation to select instructor template
    content, error = templates.render_obj(
        course, 
        {"request": request},
        variation="instructor"
    )
    
    if error:
        raise HTTPException(status_code=500, detail="Template error")
    
    return HTMLResponse(content=content)


@app.get("/courses/{course_id}/student")
@smart_response("course/student_view.html")
async def get_course_student_view(request: Request, course_id: int):
    """Student view of course - demonstrates template variations."""
    course = next((c for c in courses if c.id == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Find student enrollment for this course
    enrollment = next((e for e in enrollments if e.course_id == course_id), None)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    return enrollment


# API routes (JSON-only)
@app.get("/api/schools")
async def api_list_schools():
    """API endpoint - should return JSON regardless of Accept header."""
    return {"schools": [s.to_template_dict() for s in schools]}


@app.get("/api/schools/{school_id}")
async def api_get_school(school_id: int):
    """API endpoint for school data."""
    school = next((s for s in schools if s.id == school_id), None)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school.to_template_dict()


@app.get("/api/students/{student_id}")
async def api_get_student(student_id: int):
    """API endpoint for student data."""
    student = next((s for s in students if s.id == student_id), None)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student.to_template_dict()


@app.get("/api/courses/{course_id}")
async def api_get_course(course_id: int):
    """API endpoint for course data."""
    course = next((c for c in courses if c.id == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course.to_template_dict()


# Error demonstration routes
@app.get("/error/template")
@smart_response("nonexistent/template.html")
async def template_error(request: Request):
    """Route that triggers template error for testing error handling."""
    return {"message": "This should cause a template error"}


@app.get("/error/exception") 
async def exception_error(request: Request):
    """Route that raises an exception for testing error handling."""
    raise ValueError("This is a test exception")


@app.get("/error/missing-object")
@smart_response("student/profile.html")
async def missing_object_error(request: Request):
    """Route that returns invalid object for template."""
    return None  # Should cause template error


# Sync function demonstration
@app.get("/sync/school/{school_id}")
@smart_response("school/dashboard.html") 
def get_school_sync(request: Request, school_id: int):
    """Sync function with smart_response - tests sync/async compatibility."""
    school = next((s for s in schools if s.id == school_id), None)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school


# Content negotiation demonstration
@app.get("/demo/content-negotiation/{school_id}")
@smart_response("school/dashboard.html")
async def content_negotiation_demo(request: Request, school_id: int):
    """Demonstrates content negotiation based on Accept headers."""
    school = next((s for s in schools if s.id == school_id), None)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school