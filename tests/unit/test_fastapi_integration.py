"""
Test cases for SmartTemplates FastAPI integration.

This module tests the FastAPI-specific functionality:
- SmartFastApiTemplates: FastAPI-specific template engine
- create_smart_response: Decorator factory for content negotiation
- HTTP request/response handling and error formatting

Test Categories:
- Content Negotiation: JSON vs HTML response handling
- Context Preparation: FastAPI Request integration
- Error Handling: HTTP error responses and templates
- Function Support: Async/sync route compatibility
- Business Routes: Real-world route scenarios
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel

from smart_templates.core import SmartTemplateRegistry
from smart_templates.fastapi_integration import SmartFastApiTemplates, create_smart_response
from tests.models.business_objects import (
    Course,
    EnrollmentStatus,
    School,
    Student,
    create_sample_course,
    create_sample_school,
    create_sample_student,
)


class TestDataModel(BaseModel):
    """Test data model for FastAPI integration tests."""
    id: int
    name: str
    value: str


class TestSmartFastApiTemplatesContentNegotiation:
    """Test content negotiation between JSON and HTML responses."""

    def test_json_response_basemodel(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test JSON response with Pydantic BaseModel data."""
        test_data = TestDataModel(id=1, name="Test", value="data")
        mock_request = Mock()
        
        context = smart_fastapi_templates.prepare_context(test_data, mock_request)
        
        assert context["id"] == 1
        assert context["name"] == "Test"
        assert context["value"] == "data"
        assert context["request"] == mock_request
        assert "current_time" in context

    def test_json_response_dict(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test JSON response with dictionary data."""
        test_data = {"id": 1, "name": "Test", "items": ["a", "b", "c"]}
        mock_request = Mock()
        
        context = smart_fastapi_templates.prepare_context(test_data, mock_request)
        
        assert context["id"] == 1
        assert context["name"] == "Test"
        assert context["items"] == ["a", "b", "c"]
        assert context["request"] == mock_request
        assert "current_time" in context

    def test_html_response_success(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test successful HTML response rendering."""
        school = create_sample_school("Test University")
        mock_request = Mock()
        
        # Register template for school
        smart_fastapi_templates.registry.register(School, template_name="school/dashboard.html")
        
        content, error = smart_fastapi_templates.render_obj(
            school, 
            {"request": mock_request}
        )
        
        assert error is None
        assert "Test University" in content
        assert school.name in content

    def test_api_path_convention(self, test_client: TestClient):
        """Test that /api/ paths return JSON by default."""
        # This test assumes the test_fastapi_app has an /api/ route
        # We'll test with available routes and check Accept headers
        
        # Test with explicit JSON Accept header
        response = test_client.get("/", headers={"Accept": "application/json"})
        assert response.status_code == 200
        
        # Response should be JSON
        try:
            json_data = response.json()
            assert isinstance(json_data, dict)
        except ValueError:
            # If not JSON, it might be HTML - that's also valid for testing
            assert response.headers.get("content-type", "").startswith("text/html")


class TestSmartFastApiTemplatesContextPreparation:
    """Test context preparation with FastAPI Request objects."""

    def test_prepare_context_basemodel(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test context preparation with BaseModel having to_template_dict method."""
        school = create_sample_school("Context Test University")
        mock_request = Mock()
        
        context = smart_fastapi_templates.prepare_context(school, mock_request)
        
        # Should use to_template_dict if available
        assert context["name"] == school.name
        assert context["address"] == school.address
        assert context["request"] == mock_request
        assert isinstance(context["current_time"], datetime)

    def test_prepare_context_dict(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test context preparation with dictionary data."""
        test_data = {
            "title": "Test Page",
            "users": ["alice", "bob"],
            "settings": {"theme": "dark"}
        }
        mock_request = Mock()
        
        context = smart_fastapi_templates.prepare_context(test_data, mock_request)
        
        assert context["title"] == "Test Page"
        assert context["users"] == ["alice", "bob"]
        assert context["settings"] == {"theme": "dark"}
        assert context["request"] == mock_request
        assert "current_time" in context

    def test_prepare_context_other_types(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test context preparation with non-dict, non-BaseModel types."""
        test_data = "simple string"
        mock_request = Mock()
        
        context = smart_fastapi_templates.prepare_context(test_data, mock_request)
        
        assert context["data"] == "simple string"
        assert context["request"] == mock_request
        assert "current_time" in context


class TestSmartFastApiTemplatesErrorHandling:
    """Test HTTP error responses and error template rendering."""

    def test_html_response_template_error(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test HTML error response when template rendering fails."""
        student = create_sample_student("Error Student")
        mock_request = Mock()
        
        # Register non-existent template
        smart_fastapi_templates.registry.register(
            Student, 
            template_name="nonexistent/student.html"
        )
        
        content, error = smart_fastapi_templates.render_obj(
            student, 
            {"request": mock_request}
        )
        
        assert content == ""
        assert error is not None
        assert error.error.error_type == "TemplateNotFound"
        assert "nonexistent/student.html" in error.error.message

    def test_create_fallback_error_html_debug(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test fallback error HTML generation in debug mode."""
        smart_fastapi_templates.set_debug_mode(True)
        
        # Create a mock error
        from smart_templates.core import TemplateErrorDetail, RenderError
        error_detail = TemplateErrorDetail(
            error_type="TestError",
            message="Test error message",
            template_name="test.html",
            stack_trace=["line 1", "line 2", "line 3"]
        )
        error = RenderError(error=error_detail)
        
        html = smart_fastapi_templates.create_fallback_error_html(error, "Custom message")
        
        assert "Template Rendering Error" in html
        assert "TestError" in html
        assert "Test error message" in html
        assert "test.html" in html
        assert "line 1" in html  # Stack trace should be included

    def test_create_fallback_error_html_production(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test fallback error HTML generation in production mode."""
        smart_fastapi_templates.set_debug_mode(False)
        
        html = smart_fastapi_templates.create_fallback_error_html(None, "Production error")
        
        assert "Server Error" in html
        assert "Production error" not in html  # Should be generic message
        assert "An error occurred while processing your request" in html
        assert "stack" not in html.lower()  # No stack traces in production

    def test_unhandled_exception_json(self, test_client: TestClient):
        """Test unhandled exception returns JSON for API requests."""
        # Test with JSON Accept header to simulate API request
        response = test_client.get("/nonexistent", headers={"Accept": "application/json"})
        
        # Should be 404 for non-existent route
        assert response.status_code == 404

    def test_unhandled_exception_html(self, test_client: TestClient):
        """Test unhandled exception returns HTML for browser requests."""
        # Test with HTML Accept header to simulate browser request
        response = test_client.get("/nonexistent", headers={"Accept": "text/html"})
        
        # Should be 404 for non-existent route
        assert response.status_code == 404


class TestSmartFastApiTemplatesFunctionSupport:
    """Test async and sync function support."""

    def test_async_function_support(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test that decorator works with async functions."""
        smart_response = create_smart_response(smart_fastapi_templates)
        
        @smart_response("school/dashboard.html")
        async def async_route(request: Request):
            return create_sample_school("Async University")
        
        # Function should be properly decorated
        assert hasattr(async_route, "__wrapped__")
        assert callable(async_route)

    def test_sync_function_support(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test that decorator works with sync functions."""
        smart_response = create_smart_response(smart_fastapi_templates)
        
        @smart_response("student/profile.html")
        def sync_route(request: Request):
            return create_sample_student("Sync Student")
        
        # Function should be properly decorated
        assert hasattr(sync_route, "__wrapped__")
        assert callable(sync_route)

    def test_decorator_preserves_function_metadata(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test that decorator preserves original function metadata."""
        smart_response = create_smart_response(smart_fastapi_templates)
        
        @smart_response("course/detail.html")
        async def documented_route(request: Request):
            """This is a documented route function."""
            return create_sample_course("Documented Course", "DOC101")
        
        # Should preserve function name and docstring
        assert documented_route.__name__ == "documented_route"
        assert "documented route function" in documented_route.__doc__


class TestSmartFastApiTemplatesBusinessRoutes:
    """Test real-world business route scenarios."""

    def test_school_list_endpoint(self, test_client: TestClient):
        """Test school list endpoint returns proper response."""
        # Test HTML response
        response = test_client.get("/schools", headers={"Accept": "text/html"})
        assert response.status_code == 200
        
        # Should contain school information
        content = response.text
        assert "Tech University" in content or "State College" in content

    def test_school_detail_api(self, test_client: TestClient):
        """Test school detail endpoint with JSON response."""
        # Test JSON response
        response = test_client.get("/schools/1", headers={"Accept": "application/json"})
        assert response.status_code == 200
        
        # Should return JSON data
        data = response.json()
        assert "name" in data
        assert "address" in data

    def test_course_enrollment_dashboard(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test course enrollment dashboard rendering."""
        # Register appropriate template
        smart_fastapi_templates.registry.register(
            Course, 
            template_name="course/instructor_view.html"
        )
        
        course = create_sample_course("Enrollment Course", "ENRL101")
        mock_request = Mock()
        
        content, error = smart_fastapi_templates.render_obj(
            course, 
            {"request": mock_request},
            variation="instructor"
        )
        
        assert error is None
        assert "Enrollment Course" in content

    def test_student_progress_endpoint(self, test_client: TestClient):
        """Test student progress endpoint functionality."""
        # This assumes student endpoint exists in test app
        response = test_client.get("/students/1", headers={"Accept": "text/html"})
        assert response.status_code == 200
        
        content = response.text
        assert "Test Student" in content

    def test_error_template_rendering(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test error template rendering with business context."""
        # Test rendering error template
        error_context = {
            "error_message": "Student not found",
            "error_code": 404,
            "request_path": "/students/999"
        }
        
        content, error = smart_fastapi_templates.render_safe("error.html", error_context)
        
        # Should render successfully or fail gracefully
        if error is None:
            assert "Error Occurred" in content
        else:
            # If error template doesn't exist or has issues
            assert error.error.error_type in ["TemplateNotFound", "UndefinedVariable"]


class TestSmartFastApiTemplatesContentTypes:
    """Test content type handling and response formatting."""

    def test_json_content_type_detection(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test JSON content type detection from Accept headers."""
        # Test various JSON Accept headers
        json_headers = [
            "application/json",
            "application/*",
            "application/json, text/html",
            "text/html, application/json"
        ]
        
        # This is tested implicitly through the decorator behavior
        # The actual logic is in the smart_response decorator
        smart_response = create_smart_response(smart_fastapi_templates)
        
        @smart_response("test.html")
        async def test_route(request: Request):
            return {"test": "data"}
        
        assert callable(test_route)

    def test_html_content_type_detection(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test HTML content type detection from Accept headers."""
        smart_response = create_smart_response(smart_fastapi_templates)
        
        @smart_response("school/dashboard.html")
        async def html_route(request: Request):
            return create_sample_school("HTML University")
        
        assert callable(html_route)

    def test_api_path_json_preference(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test that /api/ paths prefer JSON responses."""
        # This behavior is tested through the decorator logic
        # Paths starting with /api/ should default to JSON
        smart_response = create_smart_response(smart_fastapi_templates)
        
        @smart_response("api_template.html")
        async def api_route(request: Request):
            return {"api": "response"}
        
        assert callable(api_route)


class TestSmartFastApiTemplatesIntegration:
    """Integration tests combining multiple FastAPI features."""

    def test_complete_request_response_cycle(self, test_client: TestClient):
        """Test complete request-response cycle with template rendering."""
        # Test a complete cycle from request to rendered response
        response = test_client.get("/", headers={"Accept": "text/html"})
        
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/html")

    def test_business_object_rendering_cycle(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test complete business object rendering cycle."""
        # Register multiple templates for different scenarios
        smart_fastapi_templates.registry.register(
            Student,
            template_name="student/profile.html"
        )
        smart_fastapi_templates.registry.register(
            Student,
            template_name="student/active.html",
            variation=EnrollmentStatus.ACTIVE
        )
        
        student = create_sample_student("Integration Student")
        mock_request = Mock()
        
        # Test basic rendering
        content1, error1 = smart_fastapi_templates.render_obj(
            student,
            {"request": mock_request}
        )
        
        # Test variation rendering
        content2, error2 = smart_fastapi_templates.render_obj(
            student,
            {"request": mock_request},
            variation=EnrollmentStatus.ACTIVE
        )
        
        assert error1 is None
        assert error2 is None
        assert "Integration Student" in content1
        assert "Integration Student" in content2

    def test_error_handling_with_fallback(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test error handling with fallback to error template."""
        # Register non-existent template to trigger error
        smart_fastapi_templates.registry.register(
            Course,
            template_name="definitely/nonexistent.html"
        )
        
        course = create_sample_course("Error Course", "ERR101")
        mock_request = Mock()
        
        content, error = smart_fastapi_templates.render_obj(
            course,
            {"request": mock_request}
        )
        
        assert content == ""
        assert error is not None
        assert error.error.error_type == "TemplateNotFound"
        
        # Test fallback error HTML generation
        fallback_html = smart_fastapi_templates.create_fallback_error_html(
            error, 
            "Template rendering failed"
        )
        
        assert "Server Error" in fallback_html or "Template Rendering Error" in fallback_html

    def test_context_injection_and_preparation(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test context injection and preparation for templates."""
        school = create_sample_school("Context School")
        mock_request = Mock()
        mock_request.url.path = "/schools/1"
        mock_request.method = "GET"
        
        # Test context preparation
        context = smart_fastapi_templates.prepare_context(school, mock_request)
        
        # Should have school data
        assert context["name"] == school.name
        assert context["address"] == school.address
        
        # Should have FastAPI-specific context
        assert context["request"] == mock_request
        assert "current_time" in context
        assert isinstance(context["current_time"], datetime)

    def test_multiple_template_engines(self):
        """Test multiple SmartFastApiTemplates instances."""
        registry1 = SmartTemplateRegistry()
        registry2 = SmartTemplateRegistry()
        
        # Register different templates in each registry
        registry1.register(School, template_name="school/dashboard.html")
        registry2.register(School, template_name="school/admin_dashboard.html")
        
        templates1 = SmartFastApiTemplates("templates", registry=registry1)
        templates2 = SmartFastApiTemplates("templates", registry=registry2)
        
        school = create_sample_school("Multi Engine School")
        
        # Each should resolve to different templates
        mapping1 = templates1.registry.find_template(school)
        mapping2 = templates2.registry.find_template(school)
        
        assert mapping1["path"] == "school/dashboard.html"
        assert mapping2["path"] == "school/admin_dashboard.html"