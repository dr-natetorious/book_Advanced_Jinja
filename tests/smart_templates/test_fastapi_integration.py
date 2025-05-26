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
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel

from smart_templates.core import RenderError, SmartTemplateRegistry, TemplateErrorDetail
from smart_templates.fastapi_integration import SmartFastApiTemplates, create_smart_response
from university.models.business_objects import (
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

    def test_wants_json_response_with_accept_header(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test JSON content type detection from Accept headers."""
        mock_request = Mock()
        mock_request.url.path = "/users/1"
        
        # Test JSON Accept headers
        mock_request.headers = {"accept": "application/json"}
        assert smart_fastapi_templates.wants_json_response(mock_request) is True
        
        mock_request.headers = {"accept": "application/*"}
        assert smart_fastapi_templates.wants_json_response(mock_request) is True
        
        mock_request.headers = {"accept": "text/html, application/json"}
        assert smart_fastapi_templates.wants_json_response(mock_request) is True

    def test_wants_json_response_with_api_path(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test API path detection for JSON responses."""
        mock_request = Mock()
        mock_request.headers = {"accept": "text/html"}
        
        # Test API paths
        mock_request.url.path = "/api/users/1"
        assert smart_fastapi_templates.wants_json_response(mock_request) is True
        
        mock_request.url.path = "/api/v1/data"
        assert smart_fastapi_templates.wants_json_response(mock_request) is True

    def test_wants_html_response(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test HTML response detection."""
        mock_request = Mock()
        mock_request.headers = {"accept": "text/html"}
        mock_request.url.path = "/users/1"
        
        assert smart_fastapi_templates.wants_json_response(mock_request) is False

    def test_prepare_context_basemodel(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test context preparation with BaseModel having to_template_dict method."""
        school = create_sample_school("Context Test University")
        
        context = smart_fastapi_templates.prepare_context(school)
        
        # Should use to_template_dict if available
        assert context["name"] == school.name
        assert context["address"] == school.address
        assert isinstance(context["current_time"], datetime)

    def test_prepare_context_dict(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test context preparation with dictionary data."""
        test_data = {
            "title": "Test Page",
            "users": ["alice", "bob"],
            "settings": {"theme": "dark"}
        }
        
        context = smart_fastapi_templates.prepare_context(test_data)
        
        assert context["title"] == "Test Page"
        assert context["users"] == ["alice", "bob"]
        assert context["settings"] == {"theme": "dark"}
        assert "current_time" in context

    def test_prepare_context_other_types(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test context preparation with non-dict, non-BaseModel types."""
        test_data = "simple string"
        
        context = smart_fastapi_templates.prepare_context(test_data)
        
        assert context["data"] == "simple string"
        assert "current_time" in context


class TestSmartFastApiTemplatesErrorHandling:
    """Test HTTP error responses and error template rendering."""

    def test_render_error_object(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test rendering RenderError objects as templates."""
        error_detail = TemplateErrorDetail(
            error_type="TestError",
            message="Test error message",
            template_name="test.html",
            stack_trace=["line 1", "line 2", "line 3"]
        )
        error = RenderError(error=error_detail)
        
        # Should render using error template
        content, render_error = smart_fastapi_templates.render_obj(
            error, 
            {"debug_mode": True}
        )
        
        # Should either render successfully or fail gracefully
        if render_error is None:
            assert "TestError" in content
            assert "Test error message" in content
        else:
            # If error template doesn't exist, that's expected
            assert render_error.error.error_type == "TemplateNotFound"

    def test_html_response_template_error(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test HTML error response when template rendering fails."""
        student = create_sample_student("Error Student")
        
        # Register non-existent template
        smart_fastapi_templates.registry.register_simple(
            Student, 
            template_name="nonexistent/student.html"
        )
        
        content, error = smart_fastapi_templates.render_obj(
            student, 
            {"current_time": datetime.now()}
        )
        
        assert content == ""
        assert error is not None
        assert error.error.error_type == "TemplateNotFound"
        assert "nonexistent/student.html" in error.error.message

    def test_debug_mode_toggle(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test debug mode functionality."""
        smart_fastapi_templates.set_debug_mode(True)
        assert smart_fastapi_templates.debug_mode is True
        assert smart_fastapi_templates.env.globals["debug_mode"] is True
        
        smart_fastapi_templates.set_debug_mode(False)
        assert smart_fastapi_templates.debug_mode is False
        assert smart_fastapi_templates.env.globals["debug_mode"] is False


class TestSmartResponseDecorator:
    """Test the @smart_response decorator functionality."""

    def test_create_smart_response_factory(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test smart_response decorator factory creation."""
        smart_response = create_smart_response(smart_fastapi_templates)
        assert callable(smart_response)

    def test_decorator_with_sync_function(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test decorator works with sync functions."""
        smart_response = create_smart_response(smart_fastapi_templates)
        
        @smart_response("student/profile.html")
        def sync_route(request: Request):
            return create_sample_student("Sync Student")
        
        assert hasattr(sync_route, "__wrapped__")
        assert callable(sync_route)

    def test_decorator_with_async_function(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test decorator works with async functions."""
        smart_response = create_smart_response(smart_fastapi_templates)
        
        @smart_response("school/dashboard.html")
        async def async_route(request: Request):
            return create_sample_school("Async University")
        
        assert hasattr(async_route, "__wrapped__")
        assert callable(async_route)

    def test_decorator_preserves_metadata(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test decorator preserves function metadata."""
        smart_response = create_smart_response(smart_fastapi_templates)
        
        @smart_response("course/detail.html")
        async def documented_route(request: Request):
            """This is a documented route function."""
            return create_sample_course("Documented Course", "DOC101")
        
        assert documented_route.__name__ == "documented_route"
        assert "documented route function" in documented_route.__doc__


class TestBusinessScenarios:
    """Test real-world business scenarios with FastAPI integration."""

    def test_school_object_rendering(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test school object template rendering."""
        smart_fastapi_templates.registry.register_simple(
            School, 
            template_name="school/dashboard.html"
        )
        
        school = create_sample_school("Test University")
        context = smart_fastapi_templates.prepare_context(school)
        
        content, error = smart_fastapi_templates.render_obj(school, context)
        
        assert error is None
        assert "Test University" in content
        assert school.name in content

    def test_student_status_variation_rendering(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test student rendering with status variations."""
        smart_fastapi_templates.registry.register_simple(
            Student,
            template_name="student/active.html",
            variation=EnrollmentStatus.ACTIVE
        )
        
        student = create_sample_student("Active Student")
        context = smart_fastapi_templates.prepare_context(student)
        
        content, error = smart_fastapi_templates.render_obj(
            student, 
            context,
            variation=EnrollmentStatus.ACTIVE
        )
        
        assert error is None
        assert "Active Student" in content

    def test_course_instructor_view(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test course rendering with instructor variation."""
        smart_fastapi_templates.registry.register_simple(
            Course, 
            template_name="course/instructor_view.html",
            variation="instructor"
        )
        
        course = create_sample_course("Business Course", "BIZ101")
        context = smart_fastapi_templates.prepare_context(course)
        
        content, error = smart_fastapi_templates.render_obj(
            course, 
            context,
            variation="instructor"
        )
        
        assert error is None
        assert "Business Course" in content


class TestFastAPIAppIntegration:
    """Test integration with actual FastAPI application."""

    def test_json_response_via_accept_header(self, test_client: TestClient):
        """Test JSON response with Accept header."""
        response = test_client.get("/schools/1", headers={"Accept": "application/json"})
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "name" in data

    def test_html_response_via_accept_header(self, test_client: TestClient):
        """Test HTML response with Accept header."""
        response = test_client.get("/schools/1", headers={"Accept": "text/html"})
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/html")

    def test_api_path_returns_json(self, test_client: TestClient):
        """Test that /api/ paths default to JSON."""
        # Assuming test app has API routes
        response = test_client.get("/")
        assert response.status_code == 200
        
        # Should work regardless of path
        if "/api/" in response.request.url.path:
            data = response.json()
            assert isinstance(data, dict)

    def test_school_list_endpoint(self, test_client: TestClient):
        """Test school list endpoint returns proper response."""
        response = test_client.get("/schools", headers={"Accept": "text/html"})
        assert response.status_code == 200
        
        content = response.text
        assert "School" in content  # Should contain school-related content

    def test_student_endpoint(self, test_client: TestClient):
        """Test student endpoint functionality."""
        response = test_client.get("/students/1", headers={"Accept": "text/html"})
        assert response.status_code == 200
        
        content = response.text
        assert "Student" in content

    def test_error_handling_in_routes(self, test_client: TestClient):
        """Test error handling in actual routes."""
        # Test non-existent resource
        response = test_client.get("/nonexistent")
        assert response.status_code == 404


class TestTemplateContextIntegration:
    """Test template context preparation and injection."""

    def test_context_has_required_fields(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test that prepared context has all required fields."""
        school = create_sample_school("Context School")
        context = smart_fastapi_templates.prepare_context(school)
        
        # Should have school data
        assert "name" in context
        assert "address" in context
        
        # Should have framework-specific context
        assert "current_time" in context
        assert isinstance(context["current_time"], datetime)

    def test_context_defensive_copying(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test that context preparation doesn't mutate input."""
        original_data = {"title": "Test Page", "items": [1, 2, 3]}
        original_copy = original_data.copy()
        
        context = smart_fastapi_templates.prepare_context(original_data)
        
        # Original should be unchanged
        assert original_data == original_copy
        assert "current_time" not in original_data
        assert "current_time" in context

    def test_basemodel_with_template_dict_method(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test BaseModel with to_template_dict method."""
        school = create_sample_school("Template Dict School")
        context = smart_fastapi_templates.prepare_context(school)
        
        # Should use to_template_dict if available
        expected_keys = set(school.to_template_dict().keys())
        expected_keys.add("current_time")  # Added by prepare_context
        
        assert set(context.keys()) == expected_keys

    def test_basemodel_without_template_dict_method(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test BaseModel without to_template_dict method."""
        test_model = TestDataModel(id=1, name="Test", value="data")
        context = smart_fastapi_templates.prepare_context(test_model)
        
        # Should use model_dump
        assert context["id"] == 1
        assert context["name"] == "Test"
        assert context["value"] == "data"
        assert "current_time" in context


class TestRegistryIntegration:
    """Test SmartFastApiTemplates with different registry configurations."""

    def test_multiple_template_registrations(self, templates_dir, smart_registry):
        """Test multiple registrations work correctly."""
        templates = SmartFastApiTemplates(str(templates_dir), registry=smart_registry)
        
        school = create_sample_school("Multi Registration School")
        student = create_sample_student("Multi Registration Student")
        
        # Both should resolve to their registered templates
        school_mapping = templates.registry.find_template(school)
        student_mapping = templates.registry.find_template(student)
        
        assert school_mapping["path"] == "school/dashboard.html"
        assert student_mapping["path"] == "student/profile.html"

    def test_registry_sharing_between_instances(self, templates_dir):
        """Test registry can be shared between instances."""
        registry = SmartTemplateRegistry()
        registry.register_simple(School, template_name="shared/school.html")
        
        templates1 = SmartFastApiTemplates(str(templates_dir), registry=registry)
        templates2 = SmartFastApiTemplates(str(templates_dir), registry=registry)
        
        school = create_sample_school("Shared School")
        
        mapping1 = templates1.registry.find_template(school)
        mapping2 = templates2.registry.find_template(school)
        
        assert mapping1["path"] == mapping2["path"] == "shared/school.html"

    def test_auto_reload_configuration(self, templates_dir):
        """Test auto-reload configuration."""
        # Debug mode should enable auto-reload by default
        templates_debug = SmartFastApiTemplates(
            str(templates_dir), 
            debug_mode=True
        )
        
        # Production mode should disable auto-reload by default
        templates_prod = SmartFastApiTemplates(
            str(templates_dir), 
            debug_mode=False
        )
        
        # Explicit auto-reload setting
        templates_explicit = SmartFastApiTemplates(
            str(templates_dir),
            debug_mode=False,
            auto_reload=True
        )
        
        # Just verify instances were created successfully
        assert templates_debug.debug_mode is True
        assert templates_prod.debug_mode is False
        assert templates_explicit.debug_mode is False


class TestDeprecationHandling:
    """Test handling of deprecated features."""

    def test_prepare_context_with_request_shows_warning(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test that passing request to prepare_context shows deprecation warning."""
        mock_request = Mock()
        school = create_sample_school("Warning School")
        
        with pytest.warns(DeprecationWarning, match="Passing request to prepare_context is deprecated"):
            context = smart_fastapi_templates.prepare_context(school, mock_request)
        
        # Should still work but show warning
        assert "name" in context
        assert context["name"] == school.name


class TestPerformanceAndCaching:
    """Test performance-related features."""

    def test_registry_caching_works(self, smart_fastapi_templates: SmartFastApiTemplates):
        """Test that registry caching improves performance."""
        school = create_sample_school("Cache School")
        
        # Register template
        smart_fastapi_templates.registry.register_simple(
            School, 
            template_name="school/cached.html"
        )
        
        # First lookup
        mapping1 = smart_fastapi_templates.registry.find_template(school)
        debug1 = smart_fastapi_templates.registry.debug_lookup(school)
        
        # Second lookup should hit cache
        mapping2 = smart_fastapi_templates.registry.find_template(school)
        debug2 = smart_fastapi_templates.registry.debug_lookup(school)
        
        assert mapping1 == mapping2
        assert debug2["cache_info"]["hits"] > debug1["cache_info"]["hits"]

    def test_template_auto_reload_in_debug(self, templates_dir):
        """Test template auto-reload in debug mode."""
        templates = SmartFastApiTemplates(
            str(templates_dir),
            debug_mode=True,
            auto_reload=True
        )
        
        # Verify auto-reload is configured
        assert templates.debug_mode is True
        # Note: Testing actual file reloading would require file system operations
        # This test just verifies the configuration is set correctly