"""
Student route implementations and tests.

Demonstrates status-based template selection and enrollment scenarios.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from smart_templates.fastapi_integration import SmartFastApiTemplates, create_smart_response
from tests.models.business_objects import (
    Student,
    EnrollmentStatus,
    create_sample_student,
    create_sample_course,
    create_sample_enrollment,
    create_sample_school,
)

router = APIRouter(prefix="/students", tags=["students"])

def setup_student_routes(templates: SmartFastApiTemplates) -> APIRouter:
    """Setup student routes with template integration."""
    smart_response = create_smart_response(templates)
    
    # Register student templates with status variations
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
    templates.registry.register_simple(
        Student,
        template_name="student/reattempt.html",
        variation=EnrollmentStatus.REATTEMPT
    )
    templates.registry.register_simple(
        Student,
        template_name="student/transcript.html",
        variation="transcript"
    )
    
    @router.get("/")
    async def list_students(request: Request):
        """List all students - JSON endpoint."""
        students = [
            create_sample_student("Alice Johnson", major="Computer Science"),
            create_sample_student("Bob Smith", major="Mathematics"),
            create_sample_student("Carol Davis", major="Physics"),
            create_sample_student("David Wilson", major="Engineering"),
        ]
        for i, student in enumerate(students, 1):
            student.id = i
        
        return {"students": [s.to_template_dict() for s in students]}
    
    @router.get("/{student_id}")
    @smart_response("student/profile.html")
    async def get_student(request: Request, student_id: int):
        """Get student profile with basic information."""
        if student_id < 1 or student_id > 4:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student = create_sample_student(f"Student {student_id}", major="Computer Science")
        student.id = student_id
        
        # Add sample enrollments for demonstration
        school = create_sample_school("Sample University")
        course1 = create_sample_course("Python Programming", "CS101", school)
        course2 = create_sample_course("Data Structures", "CS201", school)
        
        enrollment1 = create_sample_enrollment(student, course1, EnrollmentStatus.ACTIVE, 75.0)
        enrollment2 = create_sample_enrollment(student, course2, EnrollmentStatus.COMPLETED, 95.0)
        
        student.enrollments.extend([enrollment1, enrollment2])
        
        return student
    
    @router.get("/{student_id}/active")
    @smart_response("student/active.html", error_template="error.html")
    async def get_active_student(request: Request, student_id: int):
        """Get student with active enrollment status view."""
        if student_id < 1 or student_id > 4:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student = create_sample_student(f"Active Student {student_id}", major="Computer Science")
        student.id = student_id
        
        # Create active enrollments
        school = create_sample_school("Active University")
        course = create_sample_course("Current Course", "ACT101", school)
        enrollment = create_sample_enrollment(student, course, EnrollmentStatus.ACTIVE, 60.0)
        student.enrollments.append(enrollment)
        
        # Use status variation for template selection
        content, error = templates.render_obj(
            student,
            {"request": request},
            variation=EnrollmentStatus.ACTIVE
        )
        
        if error:
            raise HTTPException(status_code=500, detail="Template rendering failed")
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=content)
    
    @router.get("/{student_id}/completed")
    @smart_response("student/completed.html")
    async def get_completed_student(request: Request, student_id: int):
        """Get student with completed enrollment status view."""
        if student_id < 1 or student_id > 4:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student = create_sample_student(f"Graduate {student_id}", major="Computer Science")
        student.id = student_id
        
        # Create completed enrollments
        school = create_sample_school("Graduate University")
        course = create_sample_course("Completed Course", "GRAD101", school)
        enrollment = create_sample_enrollment(student, course, EnrollmentStatus.COMPLETED, 90.0)
        student.enrollments.append(enrollment)
        
        # Use status variation for template selection
        content, error = templates.render_obj(
            student,
            {"request": request},
            variation=EnrollmentStatus.COMPLETED
        )
        
        if error:
            raise HTTPException(status_code=500, detail="Template rendering failed")
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=content)
    
    @router.get("/{student_id}/reattempt")
    @smart_response("student/reattempt.html")
    async def get_reattempt_student(request: Request, student_id: int):
        """Get student with reattempt enrollment status view."""
        if student_id < 1 or student_id > 4:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student = create_sample_student(f"Reattempt Student {student_id}", major="Computer Science")
        student.id = student_id
        
        # Create reattempt enrollments
        school = create_sample_school("Support University")
        course = create_sample_course("Challenging Course", "HARD101", school)
        enrollment = create_sample_enrollment(student, course, EnrollmentStatus.REATTEMPT, 35.0)
        student.enrollments.append(enrollment)
        
        # Use status variation for template selection
        content, error = templates.render_obj(
            student,
            {"request": request},
            variation=EnrollmentStatus.REATTEMPT
        )
        
        if error:
            raise HTTPException(status_code=500, detail="Template rendering failed")
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=content)
    
    @router.get("/{student_id}/transcript")
    @smart_response("student/transcript.html")
    async def get_student_transcript(request: Request, student_id: int):
        """Get student transcript with full enrollment history."""
        if student_id < 1 or student_id > 4:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student = create_sample_student(f"Transcript Student {student_id}", major="Computer Science")
        student.id = student_id
        
        # Create comprehensive enrollment history
        school = create_sample_school("Transcript University")
        
        courses = [
            create_sample_course("Intro to Programming", "CS101", school),
            create_sample_course("Data Structures", "CS201", school),
            create_sample_course("Algorithms", "CS301", school),
            create_sample_course("Database Systems", "CS401", school),
        ]
        
        enrollments = [
            create_sample_enrollment(student, courses[0], EnrollmentStatus.COMPLETED, 85.0),
            create_sample_enrollment(student, courses[1], EnrollmentStatus.COMPLETED, 92.0),
            create_sample_enrollment(student, courses[2], EnrollmentStatus.ACTIVE, 78.0),
            create_sample_enrollment(student, courses[3], EnrollmentStatus.REATTEMPT, 45.0),
        ]
        
        student.enrollments.extend(enrollments)
        
        return student
    
    @router.post("/")
    async def create_student(request: Request, student_data: dict):
        """Create new student (API-only endpoint)."""
        new_student = create_sample_student(
            student_data.get("name", "New Student"),
            email=student_data.get("email", "new@example.com"),
            major=student_data.get("major", "Undeclared")
        )
        new_student.id = 999  # Mock ID
        return new_student.to_template_dict()
    
    @router.put("/{student_id}")
    async def update_student(request: Request, student_id: int, student_data: dict):
        """Update existing student (API-only endpoint)."""
        if student_id < 1:
            raise HTTPException(status_code=404, detail="Student not found")
        
        updated_student = create_sample_student(
            student_data.get("name", f"Updated Student {student_id}"),
            email=student_data.get("email", f"updated{student_id}@example.com"),
            major=student_data.get("major", "Updated Major")
        )
        updated_student.id = student_id
        return updated_student.to_template_dict()
    
    @router.delete("/{student_id}")
    async def delete_student(request: Request, student_id: int):
        """Delete student (API-only endpoint)."""
        if student_id < 1:
            raise HTTPException(status_code=404, detail="Student not found")
        
        return {"message": f"Student {student_id} deleted successfully"}
    
    @router.get("/{student_id}/enrollments")
    async def get_student_enrollments(request: Request, student_id: int):
        """Get student enrollments (API-only endpoint)."""
        if student_id < 1 or student_id > 4:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Mock enrollment data
        enrollments = [
            {
                "id": 1,
                "course_title": "Python Programming",
                "course_code": "CS101",
                "status": "active",
                "progress_percentage": 75.0,
                "grade": None
            },
            {
                "id": 2,
                "course_title": "Data Structures",
                "course_code": "CS201",
                "status": "completed",
                "progress_percentage": 100.0,
                "grade": "A-"
            }
        ]
        
        return {"student_id": student_id, "enrollments": enrollments}
    
    return router


# Test functions for the student routes
async def test_student_routes():
    """Test student routes functionality."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from smart_templates.fastapi_integration import SmartFastApiTemplates
    
    # Setup test app
    app = FastAPI()
    templates = SmartFastApiTemplates("tests/fixtures/templates", debug_mode=True)
    student_router = setup_student_routes(templates)
    app.include_router(student_router)
    
    client = TestClient(app)
    
    # Test list students
    response = client.get("/students/")
    assert response.status_code == 200
    data = response.json()
    assert "students" in data
    assert len(data["students"]) == 4
    
    # Test get student - HTML
    response = client.get("/students/1", headers={"Accept": "text/html"})
    assert response.status_code == 200
    
    # Test get student - JSON
    response = client.get("/students/1", headers={"Accept": "application/json"})
    assert response.status_code == 200
    
    # Test status-specific views
    response = client.get("/students/1/active")
    assert response.status_code == 200
    
    response = client.get("/students/1/completed")
    assert response.status_code == 200
    
    response = client.get("/students/1/reattempt")
    assert response.status_code == 200
    
    response = client.get("/students/1/transcript")
    assert response.status_code == 200
    
    # Test 404
    response = client.get("/students/999")
    assert response.status_code == 404
    
    # Test CRUD operations
    response = client.post("/students/", json={"name": "Test Student", "major": "Test Major"})
    assert response.status_code == 200
    
    response = client.put("/students/1", json={"name": "Updated Student"})
    assert response.status_code == 200
    
    response = client.delete("/students/1")
    assert response.status_code == 200
    
    # Test enrollments endpoint
    response = client.get("/students/1/enrollments")
    assert response.status_code == 200
    data = response.json()
    assert "enrollments" in data


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_student_routes())