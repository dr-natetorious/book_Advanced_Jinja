"""
School route implementations and tests.

Demonstrates CRUD operations with SmartTemplates integration.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from smart_templates.fastapi_integration import SmartFastApiTemplates, create_smart_response
from tests.models.business_objects import School, create_sample_school

router = APIRouter(prefix="/schools", tags=["schools"])

def setup_school_routes(templates: SmartFastApiTemplates) -> APIRouter:
    """Setup school routes with template integration."""
    smart_response = create_smart_response(templates)
    
    # Register school templates
    templates.registry.register_simple(School, template_name="school/dashboard.html")
    templates.registry.register_simple(School, template_name="school/list.html", variation="list")
    templates.registry.register_simple(School, template_name="school/admin_dashboard.html", variation="admin")
    
    @router.get("/")
    @smart_response("school/list.html")
    async def list_schools(request: Request):
        """List all schools with content negotiation."""
        schools = [
            create_sample_school("Tech University", "San Francisco", "CA"),
            create_sample_school("State College", "Austin", "TX"),
            create_sample_school("Community College", "Portland", "OR"),
        ]
        for i, school in enumerate(schools, 1):
            school.id = i
        return {"schools": schools}
    
    @router.get("/{school_id}")
    @smart_response("school/dashboard.html")
    async def get_school(request: Request, school_id: int):
        """Get school by ID with dashboard view."""
        if school_id < 1 or school_id > 3:
            raise HTTPException(status_code=404, detail="School not found")
        
        school = create_sample_school(f"School {school_id}", "Test City", "CA")
        school.id = school_id
        return school
    
    @router.get("/{school_id}/admin")
    @smart_response("school/admin_dashboard.html")
    async def get_school_admin(request: Request, school_id: int):
        """Get school admin dashboard with administrative controls."""
        if school_id < 1 or school_id > 3:
            raise HTTPException(status_code=404, detail="School not found")
            
        school = create_sample_school(f"Admin View - School {school_id}", "Admin City", "CA")
        school.id = school_id
        
        # Add sample courses for admin view
        from tests.models.business_objects import create_sample_course
        course1 = create_sample_course("Computer Science 101", "CS101", school)
        course2 = create_sample_course("Mathematics 201", "MATH201", school)
        course3 = create_sample_course("Physics 301", "PHYS301", school)
        
        school.courses.extend([course1, course2, course3])
        
        return school
    
    @router.post("/")
    async def create_school(request: Request, school_data: dict):
        """Create new school (API-only endpoint)."""
        # Simplified creation for testing
        new_school = create_sample_school(
            school_data.get("name", "New School"),
            school_data.get("city", "Unknown City"),
            school_data.get("state", "Unknown State")
        )
        new_school.id = 999  # Mock ID
        return new_school.to_template_dict()
    
    @router.put("/{school_id}")
    async def update_school(request: Request, school_id: int, school_data: dict):
        """Update existing school (API-only endpoint)."""
        if school_id < 1:
            raise HTTPException(status_code=404, detail="School not found")
            
        updated_school = create_sample_school(
            school_data.get("name", f"Updated School {school_id}"),
            school_data.get("city", "Updated City"),
            school_data.get("state", "Updated State")
        )
        updated_school.id = school_id
        return updated_school.to_template_dict()
    
    @router.delete("/{school_id}")
    async def delete_school(request: Request, school_id: int):
        """Delete school (API-only endpoint)."""
        if school_id < 1:
            raise HTTPException(status_code=404, detail="School not found")
            
        return {"message": f"School {school_id} deleted successfully"}
    
    return router


# Test functions for the school routes
async def test_school_routes():
    """Test school routes functionality."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from smart_templates.fastapi_integration import SmartFastApiTemplates
    
    # Setup test app
    app = FastAPI()
    templates = SmartFastApiTemplates("tests/fixtures/templates", debug_mode=True)
    school_router = setup_school_routes(templates)
    app.include_router(school_router)
    
    client = TestClient(app)
    
    # Test list schools - HTML
    response = client.get("/schools/", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    
    # Test list schools - JSON
    response = client.get("/schools/", headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "schools" in data
    assert len(data["schools"]) == 3
    
    # Test get school - HTML
    response = client.get("/schools/1", headers={"Accept": "text/html"})
    assert response.status_code == 200
    
    # Test get school - JSON
    response = client.get("/schools/1", headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    
    # Test admin view
    response = client.get("/schools/1/admin", headers={"Accept": "text/html"})
    assert response.status_code == 200
    
    # Test 404
    response = client.get("/schools/999")
    assert response.status_code == 404
    
    # Test CRUD operations
    response = client.post("/schools/", json={"name": "Test School", "city": "Test City"})
    assert response.status_code == 200
    
    response = client.put("/schools/1", json={"name": "Updated School"})
    assert response.status_code == 200
    
    response = client.delete("/schools/1")
    assert response.status_code == 200


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_school_routes())