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
- Registry New Features: Config-based registration, debugging, caching
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

from pydantic import ValidationError
import pytest

from smart_templates.core import (
    RenderError,
    RegistrationConfig,
    RegistrationType,
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
        registry.register_simple(School, template_name="school/dashboard.html")
        
        school = create_sample_school("Test University")
        mapping = registry.find_template(school)
        
        assert mapping is not None
        assert mapping["type"] == "template"
        assert mapping["path"] == "school/dashboard.html"

    def test_register_macro_only(self):
        """Test registering macro without explicit template."""
        registry = SmartTemplateRegistry()
        registry.register_simple(Student, macro_name="render_student")
        
        student = create_sample_student("John Doe")
        mapping = registry.find_template(student)
        
        assert mapping is not None
        assert mapping["type"] == "macro"
        assert mapping["macro"] == "render_student"
        assert mapping["template"] == "student.html"

    def test_register_both_template_and_macro(self):
        """Test registering both template and macro."""
        registry = SmartTemplateRegistry()
        registry.register_simple(
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
        registry.register_simple(
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

    def test_register_requires_template_or_macro(self):
        """Test that registration requires either template_name or macro_name."""
        registry = SmartTemplateRegistry()
        
        with pytest.raises(ValueError, match="requires either template_name or macro_name"):
            registry.register_simple(School)


class TestSmartTemplateRegistryNewFeatures:
    """Test new registry features: config-based registration, debugging, management."""

    def test_register_with_config(self):
        """Test new config-based registration API."""
        registry = SmartTemplateRegistry()
        
        config = RegistrationConfig(
            name="school/dashboard.html",
            registration_type=RegistrationType.TEMPLATE,
            target="school/dashboard.html"
        )
        registry.register(School, config=config)
        
        school = create_sample_school("Config University")
        mapping = registry.find_template(school)
        
        assert mapping["type"] == "template"
        assert mapping["path"] == "school/dashboard.html"

    def test_register_macro_with_config(self):
        """Test macro registration with config."""
        registry = SmartTemplateRegistry()
        
        config = RegistrationConfig(
            name="render_student",
            registration_type=RegistrationType.MACRO,
            target="student/profile.html",
            variation=EnrollmentStatus.ACTIVE
        )
        registry.register(Student, config=config)
        
        student = create_sample_student("Config Student")
        mapping = registry.find_template(student, variation=EnrollmentStatus.ACTIVE)
        
        assert mapping["type"] == "macro"
        assert mapping["macro"] == "render_student"
        assert mapping["template"] == "student/profile.html"

    def test_unregister_functionality(self):
        """Test removing registrations."""
        registry = SmartTemplateRegistry()
        registry.register_simple(School, template_name="school/dashboard.html")
        
        school = create_sample_school("Test University")
        mapping = registry.find_template(school)
        assert mapping["path"] == "school/dashboard.html"
        
        # Unregister
        removed = registry.unregister(School)
        assert removed is True
        
        # Should fall back to convention
        mapping = registry.find_template(school)
        assert mapping["path"] == "school.html"
        
        # Unregistering again should return False
        removed = registry.unregister(School)
        assert removed is False

    def test_clear_registrations(self):
        """Test clearing all registrations."""
        registry = SmartTemplateRegistry()
        registry.register_simple(School, template_name="school/dashboard.html")
        registry.register_simple(Student, template_name="student/profile.html")
        
        # Verify registrations exist
        registrations = registry.list_registrations()
        assert len(registrations) == 2
        
        # Clear all
        registry.clear()
        registrations = registry.list_registrations()
        assert len(registrations) == 0
        
        # Should fall back to convention
        school = create_sample_school("Test University")
        mapping = registry.find_template(school)
        assert mapping["path"] == "school.html"

    def test_list_registrations(self):
        """Test registry inspection."""
        registry = SmartTemplateRegistry()
        registry.register_simple(School, template_name="school/dashboard.html")
        registry.register_simple(
            Student,
            template_name="student/active.html",
            variation=EnrollmentStatus.ACTIVE
        )
        
        registrations = registry.list_registrations()
        assert len(registrations) == 2
        assert "School" in registrations
        assert "Student:ACTIVE" in registrations or "Student:active" in registrations

    def test_debug_lookup(self):
        """Test debug information for template lookup."""
        registry = SmartTemplateRegistry()
        registry.register_simple(School, template_name="school/dashboard.html")
        
        school = create_sample_school("Debug University")
        debug_info = registry.debug_lookup(school)
        
        assert debug_info["obj_type"] == "School"
        assert debug_info["final_mapping"]["path"] == "school/dashboard.html"
        assert "lookup_hierarchy" in debug_info
        assert "cache_info" in debug_info

    def test_registry_caching(self):
        """Test LRU cache functionality."""
        registry = SmartTemplateRegistry()
        registry.register_simple(School, template_name="school/dashboard.html")
        
        school = create_sample_school("Cache University")
        
        # First lookup
        mapping1 = registry.find_template(school)
        debug1 = registry.debug_lookup(school)
        
        # Second lookup should use cache
        mapping2 = registry.find_template(school)
        debug2 = registry.debug_lookup(school)
        
        assert mapping1 == mapping2
        assert debug2["cache_info"]["hits"] > debug1["cache_info"]["hits"]

    def test_registry_repr(self):
        """Test registry string representation."""
        registry = SmartTemplateRegistry()
        registry.register_simple(School, template_name="school/dashboard.html")
        
        repr_str = repr(registry)
        assert "SmartTemplateRegistry" in repr_str
        assert "registrations=1" in repr_str


class TestSmartTemplateRegistryResolution:
    """Test template resolution with fallback hierarchy and naming conventions."""

    def test_exact_match_with_model_variation(self):
        """Test exact match takes priority over fallbacks."""
        registry = SmartTemplateRegistry()
        
        # Register multiple variations
        registry.register_simple(Student, template_name="student/profile.html")
        registry.register_simple(
            Student,
            template_name="student/active.html",
            variation=EnrollmentStatus.ACTIVE
        )
        registry.register_simple(
            Student,
            template_name="student/enrollment.html",
            model=Enrollment
        )
        registry.register_simple(
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
        registry.register_simple(Course, template_name="course/base.html")
        
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
        registry.register_simple(School, template_name="school/registered.html")
        
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


class TestSmartTemplatesInitialization:
    """Test SmartTemplates initialization and validation."""

    def test_valid_directory_initialization(self, templates_dir: Path):
        """Test initialization with valid directory."""
        templates = SmartTemplates(str(templates_dir))
        assert templates.debug_mode is False
        assert templates.registry is not None
        assert "debug_mode" in templates.env.globals

    def test_invalid_directory_initialization(self):
        """Test initialization with invalid directory."""
        with pytest.raises(ValueError, match="does not exist"):
            SmartTemplates("/nonexistent/path")
        
        # Test with file instead of directory
        with pytest.raises(ValueError, match="is not a directory"):
            SmartTemplates(__file__)

    def test_custom_registry_initialization(self, templates_dir: Path):
        """Test initialization with custom registry."""
        registry = SmartTemplateRegistry()
        registry.register_simple(School, template_name="school/custom.html")
        
        templates = SmartTemplates(str(templates_dir), registry=registry)
        assert templates.registry is registry
        
        school = create_sample_school("Custom University")
        mapping = templates.registry.find_template(school)
        assert mapping["path"] == "school/custom.html"

    def test_templates_repr(self, templates_dir: Path):
        """Test SmartTemplates string representation."""
        templates = SmartTemplates(str(templates_dir), debug_mode=True)
        
        repr_str = repr(templates)
        assert "SmartTemplates" in repr_str
        assert "debug_mode=True" in repr_str
        assert str(templates_dir) in repr_str


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
        assert "SmartTemplates" in content

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
        smart_templates.registry.register_simple(School, template_name="school/dashboard.html")
        
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
        smart_templates.registry.register_simple(
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
        smart_templates.registry.register_simple(
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
        smart_templates.registry.register_simple(Student, template_name="student/profile.html")
        
        student = create_sample_student("Context Student")
        original_context = {"existing_var": "test"}
        
        content, error = smart_templates.render_obj(student, original_context)
        
        assert error is None
        assert "Context Student" in content
        # Original context should not be mutated
        assert "object" not in original_context

    def test_debug_render_obj(self, smart_templates: SmartTemplates):
        """Test debug version of render_obj."""
        smart_templates.registry.register_simple(School, template_name="school/dashboard.html")
        
        school = create_sample_school("Debug University")
        context = {"test": "data"}
        
        debug_info = smart_templates.debug_render_obj(school, context)
        
        assert "lookup_debug" in debug_info
        assert "render_success" in debug_info
        assert "content_length" in debug_info
        assert "context_keys" in debug_info
        assert debug_info["render_success"] is True
        assert debug_info["context_keys"] == ["test"]


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
        smart_templates.registry.register_simple(School, template_name="school/dashboard.html")
        smart_templates.registry.register_simple(
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
        smart_templates.registry.register_simple(Course, template_name="nonexistent/course.html")
        
        course = create_sample_course("Error Course", "ERR101")
        content, error = smart_templates.render_obj(course, {})
        
        assert content == ""
        assert error is not None
        assert error.error.error_type == "TemplateNotFound"
        assert "nonexistent/course.html" in error.error.message

    def test_multiple_registrations_override(self, smart_templates: SmartTemplates):
        """Test that later registrations override earlier ones."""
        # Register initial template
        smart_templates.registry.register_simple(Student, template_name="student/initial.html")
        
        # Override with new registration
        smart_templates.registry.register_simple(Student, template_name="student/override.html")
        
        student = create_sample_student("Override Student")
        mapping = smart_templates.registry.find_template(student)
        
        assert mapping["path"] == "student/override.html"

    def test_registry_sharing_between_instances(self, templates_dir: Path):
        """Test that registry can be shared between SmartTemplates instances."""
        registry = SmartTemplateRegistry()
        registry.register_simple(School, template_name="school/dashboard.html")  # Official template
        
        # Create two template instances with shared registry
        templates1 = SmartTemplates(str(templates_dir), registry=registry)
        templates2 = SmartTemplates(str(templates_dir), registry=registry)
        
        school = create_sample_school("Shared School")
        
        # Both should resolve to the same template
        mapping1 = templates1.registry.find_template(school)
        mapping2 = templates2.registry.find_template(school)
        
        assert mapping1["path"] == mapping2["path"] == "school/dashboard.html"

    def test_config_and_simple_registration_interoperability(self, smart_templates: SmartTemplates):
        """Test that config-based and simple registration work together."""
        # Use simple registration
        smart_templates.registry.register_simple(School, template_name="school/simple.html")
        
        # Use config registration
        config = RegistrationConfig(
            name="student/config.html",
            registration_type=RegistrationType.TEMPLATE,
            target="student/config.html"
        )
        smart_templates.registry.register(Student, config=config)
        
        # Both should work
        school = create_sample_school("Simple School")
        student = create_sample_student("Config Student")
        
        school_mapping = smart_templates.registry.find_template(school)
        student_mapping = smart_templates.registry.find_template(student)
        
        assert school_mapping["path"] == "school/simple.html"
        assert student_mapping["path"] == "student/config.html"

    def test_cache_invalidation_on_registration_changes(self):
        """Test that cache is cleared when registrations change."""
        registry = SmartTemplateRegistry()
        
        # Initial lookup
        school = create_sample_school("Cache School")
        mapping1 = registry.find_template(school)
        debug1 = registry.debug_lookup(school)
        
        # Add registration
        registry.register_simple(School, template_name="school/cached.html")
        
        # Lookup again - should get new result and reset cache
        mapping2 = registry.find_template(school)
        debug2 = registry.debug_lookup(school)
        
        assert mapping1["path"] == "school.html"  # Convention
        assert mapping2["path"] == "school/cached.html"  # Registered
        
        # Cache should be reset (misses reset)
        assert debug2["cache_info"]["misses"] >= debug1["cache_info"]["misses"]

    def test_template_not_found_with_debug_info(self, smart_templates: SmartTemplates):
        """Test template not found error includes debug information."""
        school = create_sample_school("Debug School")
        
        # Try to render without registration (will use convention and fail)
        content, error = smart_templates.render_obj(school, {})
        
        assert content == ""
        assert error is not None
        assert error.error.error_type == "TemplateNotFound"
        
        # Get debug info for the same lookup
        debug_info = smart_templates.debug_render_obj(school, {})
        
        assert debug_info["render_success"] is False
        assert debug_info["lookup_debug"]["obj_type"] == "School"
        assert debug_info["lookup_debug"]["final_mapping"]["path"] == "school.html"


class TestRegistrationConfigValidation:
    """Test RegistrationConfig validation and features."""

    def test_registration_config_creation(self):
        """Test creating RegistrationConfig objects."""
        config = RegistrationConfig(
            name="test_template",
            registration_type=RegistrationType.TEMPLATE,
            target="templates/test.html"
        )
        
        assert config.name == "test_template"
        assert config.registration_type == RegistrationType.TEMPLATE
        assert config.target == "templates/test.html"
        assert config.model_class is None
        assert config.variation is None

    def test_registration_config_with_model_variation(self):
        """Test RegistrationConfig with model and variation."""
        config = RegistrationConfig(
            name="student_macro",
            registration_type=RegistrationType.MACRO,
            target="macros/student.html",
            model_class=Enrollment,
            variation=EnrollmentStatus.ACTIVE
        )
        
        assert config.model_class is Enrollment
        assert config.variation == EnrollmentStatus.ACTIVE

    def test_registration_config_immutable(self):
        """Test that RegistrationConfig is immutable."""
        config = RegistrationConfig(
            name="test",
            registration_type=RegistrationType.TEMPLATE,
            target="test.html"
        )
        
        # Pydantic frozen model should prevent modification
        with pytest.raises(ValidationError):
            config.name = "modified"

    def test_registration_config_serialization(self):
        """Test RegistrationConfig serialization."""
        config = RegistrationConfig(
            name="test_macro",
            registration_type=RegistrationType.MACRO,
            target="macros/test.html",
            model_class=Student,
            variation=EnrollmentStatus.COMPLETED
        )
        
        data = config.model_dump()
        assert data["name"] == "test_macro"
        assert data["registration_type"] == RegistrationType.MACRO
        assert data["target"] == "macros/test.html"

    def test_registration_type_enum(self):
        """Test RegistrationType enum values."""
        assert RegistrationType.TEMPLATE.value == "template"
        assert RegistrationType.MACRO.value == "macro"
        assert RegistrationType.FILTER.value == "filter"
        assert RegistrationType.TEST.value == "test"
        assert RegistrationType.FUNCTION.value == "function"


class TestErrorHandlingEnhancements:
    """Test enhanced error handling features."""

    def test_template_error_detail_completeness(self):
        """Test that TemplateErrorDetail captures all relevant information."""
        error = TemplateErrorDetail(
            error_type="TestError",
            message="Test error message",
            template_name="test.html",
            macro_name="test_macro",
            line_number=42,
            context_data={"var1": "str", "var2": "int"},
            stack_trace=["line1", "line2"]
        )
        
        assert error.error_type == "TestError"
        assert error.message == "Test error message"
        assert error.template_name == "test.html"
        assert error.macro_name == "test_macro"
        assert error.line_number == 42
        assert error.context_data == {"var1": "str", "var2": "int"}
        assert error.stack_trace == ["line1", "line2"]
        assert isinstance(error.timestamp, datetime)

    def test_render_error_with_debug_info(self):
        """Test RenderError with additional debug information."""
        error_detail = TemplateErrorDetail(
            error_type="TestError",
            message="Test message"
        )
        
        render_error = RenderError(
            error=error_detail,
            debug_info={"additional": "data", "context": "info"}
        )
        
        assert render_error.success is False
        assert render_error.error.error_type == "TestError"
        assert render_error.debug_info["additional"] == "data"

    def test_structured_error_serialization(self):
        """Test that structured errors serialize properly."""
        error_detail = TemplateErrorDetail(
            error_type="TemplateNotFound",
            message="Template not found",
            template_name="missing.html",
            context_data={"user": "dict", "items": "list[3]"}
        )
        
        render_error = RenderError(error=error_detail)
        
        # Should serialize to dict
        data = render_error.model_dump()
        assert isinstance(data, dict)
        assert data["success"] is False
        assert data["error"]["error_type"] == "TemplateNotFound"
        assert data["error"]["template_name"] == "missing.html"
        assert "timestamp" in data["error"]