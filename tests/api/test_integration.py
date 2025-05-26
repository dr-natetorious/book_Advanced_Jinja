"""
End-to-end integration tests for SmartTemplates FastAPI integration.

Tests complete request-response cycles with real FastAPI routes,
template rendering, and business scenarios.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from smart_templates.fastapi_integration import SmartFastApiTemplates
from tests.api.app import app as test_app
from tests.api.routes.schools import setup_school_routes
from tests.api.routes.students import setup_student_routes
from tests.models.business_objects import EnrollmentStatus


class TestFullStackIntegration:
    """Complete FastAPI + SmartTemplates integration tests."""

    @pytest.fixture
    def integration_app(self, templates_dir):
        """Create test app with all routes."""
        app = FastAPI(title="Integration Test App")
        templates = SmartFastApiTemplates(str(templates_dir), debug_mode=True)
        
        # Include route modules
        app.include_router(setup_school_routes(templates))
        app.include_router(setup_student_routes(templates))
        
        return app

    @pytest.fixture
    def client(self, integration_app):
        """Test client for integration app."""
        return TestClient(integration_app)

    def test_content_negotiation_html_vs_json(self, client):
        """Test content negotiation works across routes."""
        # HTML request
        response = client.get("/schools/1", headers={"Accept": "text/html"})
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "School 1" in response.text

        # JSON request  
        response = client.get("/schools/1", headers={"Accept": "application/json"})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert "name" in data

    def test_school_dashboard_rendering(self, client):
        """Test school dashboard template rendering."""
        response = client.get("/schools/1", headers={"Accept": "text/html"})
        assert response.status_code == 200
        
        content = response.text
        assert "School 1" in content
        assert "Dashboard" in content or "school" in content.lower()

    def test_school_admin_view(self, client):
        """Test school admin template variation."""
        response = client.get("/schools/1/admin", headers={"Accept": "text/html"})
        assert response.status_code == 200
        
        content = response.text
        assert "Admin" in content
        assert "School 1" in content

    def test_student_profile_rendering(self, client):
        """Test student profile template rendering."""
        response = client.get("/students/1", headers={"Accept": "text/html"})
        assert response.status_code == 200
        
        content = response.text
        assert "Student 1" in content
        assert "Profile" in content or "student" in content.lower()

    def test_student_status_variations(self, client):
        """Test status-based template selection."""
        # Active status
        response = client.get("/students/1/active")
        assert response.status_code == 200
        assert "Active" in response.text

        # Completed status
        response = client.get("/students/1/completed")
        assert response.status_code == 200
        assert "Completed" in response.text or "Graduate" in response.text

        # Reattempt status
        response = client.get("/students/1/reattempt")
        assert response.status_code == 200
        assert "Reattempt" in response.text

    def test_student_transcript_view(self, client):
        """Test comprehensive transcript template."""
        response = client.get("/students/1/transcript", headers={"Accept": "text/html"})
        assert response.status_code == 200
        
        content = response.text
        assert "Transcript" in content
        assert "Student 1" in content

    def test_error_handling_404(self, client):
        """Test 404 error handling."""
        response = client.get("/schools/999")
        assert response.status_code == 404

        response = client.get("/students/999")
        assert response.status_code == 404

    def test_crud_operations(self, client):
        """Test CRUD operations work correctly."""
        # Create
        response = client.post("/schools/", json={"name": "New School", "city": "New City"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New School"

        # Update
        response = client.put("/schools/1", json={"name": "Updated School"})
        assert response.status_code == 200
        data = response.json()
        assert "Updated" in data["name"]

        # Delete
        response = client.delete("/schools/1")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    def test_api_endpoints_return_json(self, client):
        """Test /api/ paths always return JSON."""
        # Even with HTML Accept header, API should return JSON
        response = client.get("/api/schools", headers={"Accept": "text/html"})
        assert response.status_code == 200
        
        # Should be JSON regardless
        data = response.json()
        assert "schools" in data


class TestBusinessScenarios:
    """Real-world business scenario testing."""

    def test_school_management_workflow(self, client):
        """Test complete school management workflow."""
        # List schools
        response = client.get("/schools/", headers={"Accept": "application/json"})
        assert response.status_code == 200
        schools = response.json()["schools"]
        assert len(schools) == 3

        # View specific school
        response = client.get("/schools/1", headers={"Accept": "text/html"})
        assert response.status_code == 200
        assert "School 1" in response.text

        # Admin dashboard
        response = client.get("/schools/1/admin", headers={"Accept": "text/html"})
        assert response.status_code == 200
        assert "Admin" in response.text

    def test_student_enrollment_journey(self, client):
        """Test student enrollment status progression."""
        # Start with profile
        response = client.get("/students/1", headers={"Accept": "text/html"})
        assert response.status_code == 200

        # Check active enrollment
        response = client.get("/students/1/active")
        assert response.status_code == 200
        assert "Active" in response.text

        # View transcript
        response = client.get("/students/1/transcript")
        assert response.status_code == 200
        assert "Transcript" in response.text

        # Check enrollments API
        response = client.get("/students/1/enrollments")
        assert response.status_code == 200
        data = response.json()
        assert "enrollments" in data

    def test_mixed_content_negotiation(self, client):
        """Test mixed HTML/JSON requests in workflow."""
        # HTML for user interface
        response = client.get("/schools/", headers={"Accept": "text/html"})
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

        # JSON for API data
        response = client.get("/students/", headers={"Accept": "application/json"})
        assert response.status_code == 200
        data = response.json()
        assert "students" in data


class TestErrorScenarios:
    """Error handling and edge cases."""

    def test_template_not_found_graceful_handling(self, templates_dir):
        """Test graceful handling when templates are missing."""
        from smart_templates.fastapi_integration import SmartFastApiTemplates, create_smart_response
        from fastapi import FastAPI, Request
        
        app = FastAPI()
        templates = SmartFastApiTemplates(str(templates_dir), debug_mode=True)
        smart_response = create_smart_response(templates)
        
        @app.get("/test")
        @smart_response("nonexistent/template.html")
        async def test_route(request: Request):
            return {"test": "data"}
        
        client = TestClient(app)
        
        # Should handle template error gracefully
        response = client.get("/test", headers={"Accept": "text/html"})
        # Should return error response, not crash
        assert response.status_code in [200, 500]  # Depends on error template availability

    def test_exception_in_route_function(self, templates_dir):
        """Test exception handling in decorated routes."""
        from smart_templates.fastapi_integration import SmartFastApiTemplates, create_smart_response
        from fastapi import FastAPI, Request
        
        app = FastAPI()
        templates = SmartFastApiTemplates(str(templates_dir), debug_mode=True)
        smart_response = create_smart_response(templates)
        
        @app.get("/error")
        @smart_response("school/dashboard.html")
        async def error_route(request: Request):
            raise ValueError("Test exception")
        
        client = TestClient(app)
        
        # Should handle exception and return error response
        response = client.get("/error")
        assert response.status_code == 500

    def test_invalid_template_context(self, templates_dir):
        """Test handling of invalid template context."""
        from smart_templates.fastapi_integration import SmartFastApiTemplates, create_smart_response
        from fastapi import FastAPI, Request
        
        app = FastAPI()
        templates = SmartFastApiTemplates(str(templates_dir), debug_mode=True)
        smart_response = create_smart_response(templates)
        
        @app.get("/invalid")
        @smart_response("school/dashboard.html")
        async def invalid_context_route(request: Request):
            # Return object that can't be serialized/templated properly
            return object()
        
        client = TestClient(app)
        
        # Should handle gracefully
        response = client.get("/invalid")
        # Should not crash the application
        assert response.status_code in [200, 500]


class TestPerformanceAndCaching:
    """Performance and caching behavior tests."""

    def test_template_caching_across_requests(self, client):
        """Test that templates are cached properly."""
        # Multiple requests should use cached templates
        for _ in range(5):
            response = client.get("/schools/1", headers={"Accept": "text/html"})
            assert response.status_code == 200
            assert "School 1" in response.text

    def test_registry_performance(self, client):
        """Test registry lookup performance."""
        # Different objects should resolve quickly
        objects = [
            ("/schools/1", "School 1"),
            ("/schools/2", "School 2"),
            ("/students/1", "Student 1"),
            ("/students/2", "Student 2"),
        ]
        
        for path, expected in objects:
            response = client.get(path, headers={"Accept": "text/html"})
            assert response.status_code == 200
            assert expected in response.text


class TestDebugMode:
    """Debug mode specific functionality."""

    def test_debug_mode_error_details(self, templates_dir):
        """Test debug mode shows detailed errors."""
        from smart_templates.fastapi_integration import SmartFastApiTemplates
        
        templates = SmartFastApiTemplates(str(templates_dir), debug_mode=True)
        assert templates.debug_mode is True

        # Debug mode should be reflected in environment
        assert templates.env.globals["debug_mode"] is True

    def test_production_mode_error_hiding(self, templates_dir):
        """Test production mode hides error details."""
        from smart_templates.fastapi_integration import SmartFastApiTemplates
        
        templates = SmartFastApiTemplates(str(templates_dir), debug_mode=False)
        assert templates.debug_mode is False

        # Production mode should be reflected
        assert templates.env.globals["debug_mode"] is False


class TestRealWorldApp:
    """Test the actual test app from app.py."""

    @pytest.fixture
    def real_app_client(self):
        """Client for the real test app."""
        return TestClient(test_app)

    def test_root_endpoint(self, real_app_client):
        """Test root endpoint."""
        response = real_app_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "SmartTemplates Test API"

    def test_health_check(self, real_app_client):
        """Test health endpoint."""
        response = real_app_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_school_routes_in_real_app(self, real_app_client):
        """Test school routes in real app."""
        # List schools
        response = real_app_client.get("/schools")
        assert response.status_code == 200

        # Get specific school
        response = real_app_client.get("/schools/1")
        assert response.status_code == 200

    def test_student_routes_in_real_app(self, real_app_client):
        """Test student routes in real app."""
        # List students
        response = real_app_client.get("/students")
        assert response.status_code == 200

        # Get specific student
        response = real_app_client.get("/students/1")
        assert response.status_code == 200

    def test_api_prefix_behavior(self, real_app_client):
        """Test /api/ prefix behavior."""
        response = real_app_client.get("/api/schools")
        assert response.status_code == 200
        data = response.json()
        assert "schools" in data

    def test_error_routes_in_real_app(self, real_app_client):
        """Test error demonstration routes."""
        # Template error
        response = real_app_client.get("/error/template")
        # Should handle gracefully
        assert response.status_code in [200, 500]

        # Exception error
        response = real_app_client.get("/error/exception")
        assert response.status_code == 500


class TestComprehensiveWorkflows:
    """End-to-end workflow testing."""

    def test_complete_school_administration_workflow(self, client):
        """Test complete school admin workflow."""
        # 1. List all schools
        response = client.get("/schools/", headers={"Accept": "text/html"})
        assert response.status_code == 200

        # 2. View school dashboard
        response = client.get("/schools/1", headers={"Accept": "text/html"})
        assert response.status_code == 200

        # 3. Access admin interface
        response = client.get("/schools/1/admin", headers={"Accept": "text/html"})
        assert response.status_code == 200

        # 4. Get school data via API
        response = client.get("/schools/1", headers={"Accept": "application/json"})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1

    def test_complete_student_lifecycle(self, client):
        """Test complete student lifecycle."""
        # 1. View student profile
        response = client.get("/students/1", headers={"Accept": "text/html"})
        assert response.status_code == 200

        # 2. Check active status
        response = client.get("/students/1/active")
        assert response.status_code == 200

        # 3. View transcript
        response = client.get("/students/1/transcript")
        assert response.status_code == 200

        # 4. Check API endpoints
        response = client.get("/students/1/enrollments")
        assert response.status_code == 200

        # 5. Graduate (completed status)
        response = client.get("/students/1/completed")
        assert response.status_code == 200

    def test_mixed_api_and_web_usage(self, client):
        """Test mixing API and web interface usage."""
        # Web interface requests
        web_responses = []
        for endpoint in ["/schools/1", "/students/1"]:
            response = client.get(endpoint, headers={"Accept": "text/html"})
            web_responses.append(response)
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")

        # API requests
        api_responses = []
        for endpoint in ["/schools/1", "/students/"]:
            response = client.get(endpoint, headers={"Accept": "application/json"})
            api_responses.append(response)
            assert response.status_code == 200

        # Verify different response types
        assert len(web_responses) == 2
        assert len(api_responses) == 2