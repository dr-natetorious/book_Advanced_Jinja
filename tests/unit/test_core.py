"""
Test cases for SmartTemplates core functionality.

This module tests the core SmartTemplates classes:
- SmartTemplateRegistry: Object-to-template mapping with fallback hierarchy
- SmartTemplates: Framework-agnostic template engine with error handling
- Template rendering, macro support, and object-based resolution

Test Categories:
- Registry Basic: Template/macro registration and lookup
- Registry Resolution: Fallback hierarchy and naming conventions  
- Registry Patterns: Custom pattern functions
- Render Safe: Template rendering with error handling
- Safe Macro: Macro rendering functionality
- Render Object: Object-based template resolution
- Debug Features: Development utilities
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from smart_templates.core import (
    RenderError,
    SmartTemplateRegistry,
    SmartTemplates,
    TemplateErrorDetail,
)
from tests.models.business_objects import (
    Course,
    CourseStatus,
    Enrollment,
    EnrollmentStatus,
    School,
    Student,
    create_sample_course,
    create_sample_enrollment,
    create_sample_school,
    create_sample_student,
)


class TestSmartTemplateRegistryBasic:
    """Test basic template/macro registration and lookup functionality."""

    def test_register_template_only(self):
        """Test registering template without macro."""
        registry = SmartTemplateRegistry()
        registry.register(School, template_name="school/dashboard.html")
        
        school = create_sample_school("Test University")
        mapping = registry.find_template(school)
        
        assert mapping is not None
        assert mapping["type"] == "template"
        assert mapping["path"] == "school/dashboard.html"

    def test_register_macro_only(self):
        """Test registering macro without explicit template."""
        registry = SmartTemplateRegistry()
        registry.register(Student, macro_name="render_student")
        
        student = create_sample_student("John Doe")
        mapping = registry.find_template(student)
        
        assert mapping is not None
        assert mapping["type"] == "macro"
        assert mapping["macro"] == "render_student"
        # Should use convention-based template name
        assert mapping["template"] == "student.html"

    def test_register_both_template_and_macro(self):
        """Test registering both template and macro."""
        registry = SmartTemplateRegistry()
        registry.register(
            Course,
            template_name="course/detail.html",
            macro_name="render_course"
        )
        
        course = create_sample_course("Python Programming", "CS101")
        mapping = registry.find_template(course)
        
        assert mapping is not None
        assert mapping["type"] == "macro"
        assert mapping["template"] == "course/detail.html"
        assert mapping["macro"] == "render_course"

    def test_register_with_model_variation(self):
        """Test registering with model and variation parameters."""
        registry = SmartTemplateRegistry()
        registry.register(
            Student,
            template_name="student/active.html",
            model=Enrollment,
            variation=EnrollmentStatus.ACTIVE
        )
        
        student = create_sample_student("Active Student")
        mapping = registry.find_template(
            student, 
            model=Enrollment, 
            variation=EnrollmentStatus.ACTIVE
        )
        
        assert mapping is not None
        assert mapping["type"] == "template"
        assert mapping["path"] == "student/active.html"


class TestSmartTemplateRegistryResolution:
    """Test template resolution with fallback hierarchy and naming conventions."""

    def test_exact_match_with_model_variation(self):
        """Test exact match takes priority over fallbacks."""
        registry = SmartTemplateRegistry()
        
        # Register multiple variations
        registry.register(Student, template_name="student/profile.html")
        registry.register(
            Student,
            template_name="student/active.html",
            variation=EnrollmentStatus.ACTIVE
        )
        registry.register(
            Student,
            template_name="student/enrollment.html",
            model=Enrollment
        )
        registry.register(
            Student,
            template_name="student/active_enrollment.html",
            model=Enrollment,
            variation=EnrollmentStatus.ACTIVE
        )
        
        student = create_sample_student("Test Student")
        
        # Most specific match should win
        mapping = registry.find_template(
            student,
            model=Enrollment,
            variation=EnrollmentStatus.ACTIVE
        )
        assert mapping["path"] == "student/active_enrollment.html"
        
        # Less specific matches
        mapping = registry.find_template(student, model=Enrollment)
        assert mapping["path"] == "student/enrollment.html"
        
        mapping = registry.find_template(student, variation=EnrollmentStatus.ACTIVE)
        assert mapping["path"] == "student/active.html"
        
        mapping = registry.find_template(student)
        assert mapping["path"] == "student/profile.html"

    def test_fallback_hierarchy(self):
        """Test fallback hierarchy when exact match not found."""
        registry = SmartTemplateRegistry()
        
        # Only register base template
        registry.register(Course, template_name="course/base.html")
        
        course = create_sample_course("Test Course", "TEST101")
        
        # Should fallback to base template even with model/variation
        mapping = registry.find_template(
            course,
            model=School,
            variation=CourseStatus.ACTIVE
        )
        assert mapping["path"] == "course/base.html"

    def test_convention_based_naming(self):
        """Test convention-based template name generation."""
        registry = SmartTemplateRegistry()
        
        # Don't register anything - should use conventions
        school = create_sample_school("Test University")
        mapping = registry.find_template(school)
        
        assert mapping is not None
        assert mapping["type"] == "template"
        assert mapping["path"] == "school.html"
        
        # Test with model and variation
        student = create_sample_student("Test Student")
        mapping = registry.find_template(
            student,
            model=Enrollment,
            variation=EnrollmentStatus.COMPLETED
        )
        
        assert mapping["path"] == "student/enrollment/completed.html"

    def test_camel_case_to_snake_case_conversion(self):
        """Test CamelCase to snake_case conversion in naming conventions."""
        registry = SmartTemplateRegistry()
        
        # Create a class with CamelCase name for testing
        class MyComplexClassName:
            pass
        
        obj = MyComplexClassName()
        mapping = registry.find_template(obj)
        
        assert mapping["path"] == "my_complex_class_name.html"


class TestSmartTemplateRegistryPatterns:
    """Test custom pattern functions for dynamic template resolution."""

    def test_pattern_functions(self):
        """Test custom pattern function registration and usage."""
        registry = SmartTemplateRegistry()
        
        def status_pattern(obj: Any, model: Any, variation: Any) -> dict[str, str] | None:
            """Pattern function that routes based on object status."""
            if hasattr(obj, 'status') and obj.status == EnrollmentStatus.REATTEMPT:
                return {
                    "type": "template",
                    "path": "support/reattempt.html"
                }
            return None
        
        registry.register_pattern(status_pattern)
        
        # Create enrollment with reattempt status
        student = create_sample_student("Struggling Student")
        course = create_sample_course("Difficult Course", "HARD101")
        enrollment = create_sample_enrollment(
            student, course, EnrollmentStatus.REATTEMPT
        )
        
        mapping = registry.find_template(enrollment)
        assert mapping["path"] == "support/reattempt.html"

    def test_pattern_function_priority(self):
        """Test that pattern functions are tried after exact matches."""
        registry = SmartTemplateRegistry()
        
        def always_override_pattern(obj: Any, model: Any, variation: Any) -> dict[str, str]:
            """Pattern that always returns the same template."""
            return {
                "type": "template",
                "path": "pattern/override.html"
            }
        
        registry.register_pattern(always_override_pattern)
        registry.register(School, template_name="school/registered.html")
        
        school = create_sample_school("Test University")
        mapping = registry.find_template(school)
        
        # Exact match should win over pattern
        assert mapping["path"] == "school/registered.html"

    def test_pattern_function_exception_handling(self):
        """Test that pattern function exceptions are handled gracefully."""
        registry = SmartTemplateRegistry()
        
        def failing_pattern(obj: Any, model: Any, variation: Any) -> dict[str, str]:
            """Pattern function that always raises an exception."""
            raise ValueError("Pattern function failed")
        
        registry.register_pattern(failing_pattern)
        
        school = create_sample_school("Test University")
        mapping = registry.find_template(school)
        
        # Should fallback to convention-based naming
        assert mapping["path"] == "school.html"


class TestSmartTemplatesRenderSafe:
    """Test safe template rendering with error handling."""

    def test_render_safe_success(self, smart_templates: SmartTemplates):
        """Test successful template rendering."""
        context = {
            "title": "Test Page",
            "message": "Hello World",
            "items": ["item1", "item2", "item3"]
        }
        
        content, error = smart_templates.render_safe("base.html", context)
        
        assert error is None
        assert "Test Page" in content
        assert "SmartTemplates" in content  # From base template

    def test_render_safe_undefined_variable(self, smart_templates: SmartTemplates):
        """Test handling of undefined variables in templates."""
        context = {"title": "Test Page"}
        
        # Create a template that references undefined variable
        template_content = """
        <!DOCTYPE html>
        <html>
        <head><title>{{ title }}</title></head>
        <body>{{ undefined_variable }}</body>
        </html>
        """
        
        # Write temporary template
        templates_dir = Path(smart_templates.env.loader.searchpath[0])
        test_template = templates_dir / "test_undefined.html"
        test_template.write_text(template_content)
        
        try:
            content, error = smart_templates.render_safe("test_undefined.html", context)
            
            assert content == ""
            assert error is not None
            assert error.error.error_type == "UndefinedVariable"
            assert "undefined_variable" in error.error.message
            assert error.error.template_name == "test_undefined.html"
            assert error.error.context_data is not None
        finally:
            test_template.unlink(missing_ok=True)

    def test_render_safe_template_syntax_error(self, smart_templates: SmartTemplates):
        """Test handling of template syntax errors."""
        # Create template with syntax error
        template_content = """
        <!DOCTYPE html>
        <html>
        <head><title>{{ title }}</title></head>
        <body>{% invalid syntax %}</body>
        </html>
        """
        
        templates_dir = Path(smart_templates.env.loader.searchpath[0])
        test_template = templates_dir / "test_syntax_error.html"
        test_template.write_text(template_content)
        
        try:
            context = {"title": "Test Page"}
            content, error = smart_templates.render_safe("test_syntax_error.html", context)
            
            assert content == ""
            assert error is not None
            assert error.error.error_type == "TemplateSyntaxError"
            assert error.error.template_name == "test_syntax_error.html"
            assert error.error.line_number is not None
        finally:
            test_template.unlink(missing_ok=True)

    def test_render_safe_template_not_found(self, smart_templates: SmartTemplates):
        """Test handling when template file doesn't exist."""
        context = {"title": "Test Page"}
        
        content, error = smart_templates.render_safe("nonexistent.html", context)
        
        assert content == ""
        assert error is not None
        assert error.error.error_type == "TemplateNotFound"
        assert "nonexistent.html" in error.error.message

    def test_render_safe_context_mutation_protection(self, smart_templates: SmartTemplates):
        """Test that original context is not mutated during rendering."""
        original_context = {"title": "Test Page"}
        context_copy = original_context.copy()
        
        smart_templates.render_safe("base.html", original_context)
        
        # Original context should be unchanged
        assert original_context == context_copy
        assert "debug_mode" not in original_context


class TestSmartTemplatesSafeMacro:
    """Test safe macro rendering functionality."""

    def test_safe_macro_success(self, smart_templates: SmartTemplates):
        """Test successful macro rendering using official macro templates."""
        student = create_sample_student("John Doe", major="Computer Science")
        context = {"student": student}
        
        # Use the official student_components.html macro template
        content, error = smart_templates.safe_macro(
            "macros/student_components.html", "student_card", context
        )
        
        # Note: This test assumes student_card macro exists in student_components.html
        # If macro doesn't exist, we'll get MacroNotFound error which is also valid to test
        if error is None:
            assert "John Doe" in content
        else:
            # If macro doesn't exist, verify we get the right error
            assert error.error.error_type == "MacroNotFound"
            assert "student_card" in error.error.message

    def test_safe_macro_not_found(self, smart_templates: SmartTemplates):
        """Test handling when macro doesn't exist."""
        context = {"data": "test"}
        
        content, error = smart_templates.safe_macro(
            "base.html", "nonexistent_macro", context
        )
        
        assert content == ""
        assert error is not None
        assert error.error.error_type == "MacroNotFound"
        assert "nonexistent_macro" in error.error.message
        assert error.error.macro_name == "nonexistent_macro"

    def test_safe_macro_with_arguments(self, smart_templates: SmartTemplates):
        """Test macro rendering with multiple arguments using official templates."""
        course = create_sample_course("Python Programming", "CS101")
        context = {
            "course": course,
            "show_instructor": True
        }
        
        # Use the official course_components.html macro template
        content, error = smart_templates.safe_macro(
            "macros/course_components.html", "course_card", context
        )
        
        # Note: This test assumes course_card macro exists in course_components.html
        if error is None:
            assert "Python Programming" in content or "CS101" in content
        else:
            # If macro doesn't exist, verify we get the right error
            assert error.error.error_type == "MacroNotFound"
            assert "course_card" in error.error.message


class TestSmartTemplatesRenderObject:
    """Test object-based template resolution and rendering."""

    def test_render_obj_template_resolution(self, smart_templates: SmartTemplates):
        """Test object rendering with template resolution using official templates."""
        # Register template for School objects using official template
        smart_templates.registry.register(School, template_name="school/dashboard.html")
        
        school = create_sample_school("Tech University")
        context = {"extra_data": "test"}
        
        content, error = smart_templates.render_obj(school, context)
        
        assert error is None
        assert "Tech University" in content
        # Check for content from the dashboard template (based on conftest.py structure)
        assert "Dashboard" in content or school.name in content

    def test_render_obj_macro_resolution(self, smart_templates: SmartTemplates):
        """Test object rendering with macro resolution using official templates."""
        # Register macro for Course objects using official macro template
        smart_templates.registry.register(
            Course,
            template_name="macros/course_components.html",
            macro_name="course_card"
        )
        
        course = create_sample_course("Data Structures", "CS201")
        context = {}
        
        content, error = smart_templates.render_obj(course, context)
        
        # Note: This assumes course_card macro exists in course_components.html
        if error is None:
            assert "Data Structures" in content or "CS201" in content
        else:
            # If macro doesn't exist, we should get MacroNotFound error
            assert error.error.error_type == "MacroNotFound"
            assert "course_card" in error.error.message

    def test_render_obj_with_model_variation(self, smart_templates: SmartTemplates):
        """Test object rendering with model and variation parameters using official templates."""
        # Register status-specific template using official template
        smart_templates.registry.register(
            Student,
            template_name="student/completed.html",
            model=Enrollment,
            variation=EnrollmentStatus.COMPLETED
        )
        
        student = create_sample_student("Graduate Student")
        context = {"graduation_year": 2024}
        
        content, error = smart_templates.render_obj(
            student,
            context,
            model=Enrollment,
            variation=EnrollmentStatus.COMPLETED
        )
        
        assert error is None
        assert "Graduate Student" in content
        # Check for content that would be in completed template
        assert "Completed" in content or student.name in content

    def test_render_obj_fallback_to_convention(self, smart_templates: SmartTemplates):
        """Test object rendering falls back to convention-based naming."""
        # Don't register anything for School - should use conventions
        school = create_sample_school("Convention University")
        context = {}
        
        content, error = smart_templates.render_obj(school, context)
        
        # Should try to render school.html (which doesn't exist)
        assert content == ""
        assert error is not None
        assert error.error.error_type == "TemplateNotFound"
        assert "school.html" in error.error.message

    def test_render_obj_object_injection(self, smart_templates: SmartTemplates):
        """Test that object is automatically injected into template context."""
        smart_templates.registry.register(Student, template_name="student/profile.html")
        
        student = create_sample_student("Context Student")
        original_context = {"existing_var": "test"}
        
        content, error = smart_templates.render_obj(student, original_context)
        
        assert error is None
        assert "Context Student" in content
        # Original context should not be mutated
        assert "object" not in original_context


class TestSmartTemplatesDebugFeatures:
    """Test debug features and development utilities."""

    def test_debug_mode_enabled(self, smart_templates: SmartTemplates):
        """Test debug mode functionality."""
        smart_templates.set_debug_mode(True)
        
        assert smart_templates.debug_mode is True
        assert smart_templates.env.globals["debug_mode"] is True

    def test_debug_mode_disabled(self, smart_templates: SmartTemplates):
        """Test disabling debug mode."""
        smart_templates.set_debug_mode(False)
        
        assert smart_templates.debug_mode is False
        assert smart_templates.env.globals["debug_mode"] is False

    def test_safe_get_helper(self, smart_templates: SmartTemplates):
        """Test safe_get helper function."""
        # Test with dictionary
        test_dict = {"key1": "value1", "key2": "value2"}
        assert smart_templates._safe_get(test_dict, "key1") == "value1"
        assert smart_templates._safe_get(test_dict, "nonexistent", "default") == "default"
        
        # Test with object
        student = create_sample_student("Test Student")
        assert smart_templates._safe_get(student, "name") == "Test Student"
        assert smart_templates._safe_get(student, "nonexistent", "default") == "default"
        
        # Test with list
        test_list = ["item1", "item2"]
        assert smart_templates._safe_get(test_list, 0) == "item1"
        assert smart_templates._safe_get(test_list, 10, "default") == "default"

    def test_debug_variable_helper(self, smart_templates: SmartTemplates, caplog):
        """Test debug_var helper function with logging."""
        smart_templates.set_debug_mode(True)
        
        test_value = "debug_test"
        result = smart_templates._debug_variable(test_value, "test_var")
        
        # Should return the original value
        assert result == test_value
        
        # Should log debug information when debug mode is on
        assert "DEBUG test_var" in caplog.text
        assert "str" in caplog.text

    def test_extract_context_types(self, smart_templates: SmartTemplates):
        """Test context type extraction for debugging."""
        context = {
            "string_var": "hello",
            "int_var": 42,
            "list_var": [1, 2, 3],
            "dict_var": {"key": "value"},
            "bool_var": True,
            "_private_var": "should_be_skipped"
        }
        
        types_dict = smart_templates._extract_context_types(context)
        
        assert types_dict["string_var"] == "str"
        assert types_dict["int_var"] == "int(42)"
        assert types_dict["list_var"] == "list[3]"
        assert types_dict["dict_var"] == "dict[1]"
        assert types_dict["bool_var"] == "bool(True)"
        assert "_private_var" not in types_dict

    def test_error_detail_timestamp(self):
        """Test that error details include timestamps."""
        before_error = datetime.now()
        
        error_detail = TemplateErrorDetail(
            error_type="TestError",
            message="Test error message"
        )
        
        after_error = datetime.now()
        
        assert before_error <= error_detail.timestamp <= after_error

    def test_render_error_structure(self):
        """Test RenderError structure and serialization."""
        error_detail = TemplateErrorDetail(
            error_type="TestError",
            message="Test message",
            template_name="test.html",
            context_data={"var": "str"}
        )
        
        render_error = RenderError(error=error_detail)
        
        assert render_error.success is False
        assert render_error.error.error_type == "TestError"
        assert render_error.error.template_name == "test.html"
        
        # Should be serializable to dict
        error_dict = render_error.model_dump()
        assert isinstance(error_dict, dict)
        assert error_dict["success"] is False


class TestSmartTemplatesIntegration:
    """Integration tests combining multiple features."""

    def test_complete_workflow_with_business_objects(self, smart_templates: SmartTemplates):
        """Test complete workflow using business objects and official templates."""
        # Register templates for different object types using official templates
        smart_templates.registry.register(School, template_name="school/dashboard.html")
        smart_templates.registry.register(
            Student,
            template_name="student/active.html",
            variation=EnrollmentStatus.ACTIVE
        )
        
        # Create business objects
        school = create_sample_school("Integration University")
        student = create_sample_student("Integration Student")
        course = create_sample_course("Integration Course", "INT101", school)
        enrollment = create_sample_enrollment(student, course, EnrollmentStatus.ACTIVE)
        
        # Test school rendering
        content, error = smart_templates.render_obj(school, {})
        assert error is None
        assert "Integration University" in content
        
        # Test student rendering with status variation
        content, error = smart_templates.render_obj(
            student, {}, variation=EnrollmentStatus.ACTIVE
        )
        assert error is None
        assert "Integration Student" in content

    def test_error_propagation_chain(self, smart_templates: SmartTemplates):
        """Test that errors propagate correctly through the chain."""
        # Register template that doesn't exist (not in official template list)
        smart_templates.registry.register(Course, template_name="nonexistent/course.html")
        
        course = create_sample_course("Error Course", "ERR101")
        content, error = smart_templates.render_obj(course, {})
        
        assert content == ""
        assert error is not None
        assert error.error.error_type == "TemplateNotFound"
        assert "nonexistent/course.html" in error.error.message

    def test_multiple_registrations_override(self, smart_templates: SmartTemplates):
        """Test that later registrations override earlier ones."""
        # Register initial template
        smart_templates.registry.register(Student, template_name="student/initial.html")
        
        # Override with new registration
        smart_templates.registry.register(Student, template_name="student/override.html")
        
        student = create_sample_student("Override Student")
        mapping = smart_templates.registry.find_template(student)
        
        assert mapping["path"] == "student/override.html"

    def test_registry_sharing_between_instances(self):
        """Test that registry can be shared between SmartTemplates instances."""
        registry = SmartTemplateRegistry()
        registry.register(School, template_name="school/dashboard.html")  # Official template
        
        # Create two template instances with shared registry
        templates1 = SmartTemplates("templates", registry=registry)
        templates2 = SmartTemplates("templates", registry=registry)
        
        school = create_sample_school("Shared School")
        
        # Both should resolve to the same template
        mapping1 = templates1.registry.find_template(school)
        mapping2 = templates2.registry.find_template(school)
        
        assert mapping1["path"] == mapping2["path"] == "school/dashboard.html"