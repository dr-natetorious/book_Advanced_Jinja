"""SmartTemplates core module.

This module provides the core functionality for the SmartTemplates framework,
including template registry, error handling, and framework-agnostic template rendering.
"""

from __future__ import annotations

import logging
import traceback
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any, Union

from jinja2 import (
    Environment,
    FileSystemLoader,
    TemplateError,
    TemplateNotFound,
    TemplateSyntaxError,
    UndefinedError,
)
from pydantic import BaseModel, Field

# Type aliases
EnumStr = Union[str, Enum]


class TemplateErrorDetail(BaseModel):
    """Detailed information about template rendering errors."""

    error_type: str = Field(..., description="Type of error that occurred")
    message: str = Field(..., description="Human-readable error message")
    template_name: str | None = Field(
        None, description="Name of the template that caused the error"
    )
    macro_name: str | None = Field(
        None, description="Name of the macro that caused the error"
    )
    line_number: int | None = Field(
        None, description="Line number where the error occurred"
    )
    context_data: dict[str, str] | None = Field(
        None, description="Context variable types for debugging"
    )
    stack_trace: list[str] | None = Field(
        None, description="Full stack trace of the error"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When the error occurred"
    )


class RenderError(BaseModel):
    """Structured error response for template rendering failures."""

    success: bool = Field(False, description="Whether the operation was successful")
    error: TemplateErrorDetail = Field(..., description="Detailed error information")
    debug_info: dict[str, Any] | None = Field(
        None, description="Additional debug information"
    )


class SmartTemplateRegistry:
    """Registry for mapping objects to templates and macros based on type, model, and variation.

    This registry provides intelligent template resolution with fallback hierarchy
    and support for custom pattern functions.
    """

    def __init__(self) -> None:
        self._mappings: dict[str, dict[str, str]] = {}
        self._patterns: list[Callable[..., dict[str, str] | None]] = []

    def register(
        self,
        obj_type: type,
        *,
        template_name: str | None = None,
        macro_name: str | None = None,
        model: type | None = None,
        variation: EnumStr | None = None,
    ) -> None:
        """Register a specific object type to template/macro mapping.

        Args:
            obj_type: The object type to register
            template_name: Template file path for this object type
            macro_name: Macro name for this object type
            model: Optional model type for more specific mapping
            variation: Optional variation (e.g., status enum) for even more specific mapping
        """
        key = self._make_key(obj_type, model, variation)
        mapping: dict[str, str] = {}

        if template_name:
            mapping["template"] = template_name
        if macro_name:
            mapping["macro"] = macro_name

        self._mappings[key] = mapping

    def register_pattern(
        self, pattern_func: Callable[..., dict[str, str] | None]
    ) -> None:
        """Register a pattern function for dynamic template resolution.

        Args:
            pattern_func: Function that takes (obj, model, variation) and returns
                         template mapping dict or None
        """
        self._patterns.append(pattern_func)

    def find_template(
        self, obj: Any, model: type | None = None, variation: EnumStr | None = None
    ) -> dict[str, str] | None:
        """Find template/macro mapping for an object.

        Uses fallback hierarchy: exact match -> pattern functions -> convention-based

        Args:
            obj: Object to find template for
            model: Optional model type for more specific lookup
            variation: Optional variation for even more specific lookup

        Returns:
            Dictionary with template mapping information:
            - {"type": "template", "path": "..."} for template files
            - {"type": "macro", "template": "...", "macro": "..."} for macros
        """
        obj_type = type(obj)

        # Try exact matches with fallback hierarchy
        for key_parts in [
            (obj_type, model, variation),
            (obj_type, model, None),
            (obj_type, None, variation),
            (obj_type, None, None),
        ]:
            key = self._make_key(*key_parts)
            if key in self._mappings:
                mapping = self._mappings[key]
                if "macro" in mapping:
                    return {
                        "type": "macro",
                        "template": mapping.get(
                            "template",
                            self._convention_based_name(obj_type, model, variation),
                        ),
                        "macro": mapping["macro"],
                    }
                return {
                    "type": "template",
                    "path": mapping.get(
                        "template",
                        self._convention_based_name(obj_type, model, variation),
                    ),
                }

        # Try pattern functions
        for pattern_func in self._patterns:
            try:
                result = pattern_func(obj, model, variation)
                if result:
                    return result
            except Exception as e:
                # Use instance logger instead of global
                logging.getLogger(f"{__name__}.{self.__class__.__name__}").warning(
                    "Pattern function failed: %s", e
                )

        # Convention-based fallback (template)
        return {
            "type": "template",
            "path": self._convention_based_name(obj_type, model, variation),
        }

    def _make_key(
        self, obj_type: type, model: type | None, variation: EnumStr | None
    ) -> str:
        """Create lookup key for template mapping."""
        parts = [obj_type.__name__]
        if model:
            parts.append(model.__name__)
        if variation:
            parts.append(str(variation))
        return ":".join(parts)

    def _convention_based_name(self, obj_type: type, model: type | None, variation: EnumStr | None) -> str:
        # Fix CamelCase conversion
        name = obj_type.__name__
        snake_case = ""
        for i, c in enumerate(name):
            if c.isupper() and i > 0:
                snake_case += "_"
            snake_case += c.lower()
        
        parts = [snake_case]
        if model:
            # Same fix for model name
            model_snake = ""
            for i, c in enumerate(model.__name__):
                if c.isupper() and i > 0:
                    model_snake += "_"
                model_snake += c.lower()
            parts.append(model_snake)
        if variation:
            # Fix: Use enum value, not class name
            if isinstance(variation, Enum):
                parts.append(variation.value.lower())
            else:
                parts.append(str(variation).lower())
        
        return f"{'/'.join(parts)}.html"


class SmartTemplates:
    """Enhanced template engine with error handling, object-based template resolution, and macro support.

    Framework agnostic - can be used with any Python application.
    Provides structured error handling and intelligent template resolution.
    """

    def __init__(
        self,
        directory: str,
        registry: SmartTemplateRegistry | None = None,
        *,
        debug_mode: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize the template engine.

        Args:
            directory: Directory containing template files
            registry: Template registry for object-based resolution
            debug_mode: Whether to enable debug mode
            **kwargs: Additional arguments passed to Jinja2 Environment
        """
        # Create Jinja2 environment
        loader = FileSystemLoader(directory)
        self.env = Environment(loader=loader, **kwargs)
        self.registry = registry or SmartTemplateRegistry()
        self.debug_mode = debug_mode
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Add debugging helpers to template globals
        self.env.globals.update(
            {
                "debug_var": self._debug_variable,
                "safe_get": self._safe_get,
                "debug_mode": self.debug_mode,
            }
        )

    def _debug_variable(self, var: Any, var_name: str = "unknown") -> Any:
        """Helper function available in templates for debugging variables."""
        if self.debug_mode:
            self._logger.info("DEBUG %s: %s = %r", var_name, type(var).__name__, var)
        return var

    def _safe_get(self, obj: Any, key: str | int, default: Any = None) -> Any:
        try:
            # Handle integer indexing
            if isinstance(key, int) and hasattr(obj, "__getitem__"):
                return obj[key]
            # Handle string access
            if isinstance(key, str):
                if hasattr(obj, key):
                    return getattr(obj, key)
                if isinstance(obj, dict) and key in obj:
                    return obj[key]
            return default
        except (KeyError, AttributeError, TypeError, IndexError):
            return default

    def _extract_context_types(self, context: dict[str, Any]) -> dict[str, str]:
        """Extract type information from context for debugging."""
        return {
            key: (
                f"{type(value).__name__}"
                + (
                    f"[{len(value)}]"
                    if hasattr(value, "__len__") and not isinstance(value, str)
                    else f"({value})"
                    if isinstance(value, (int, float, bool, type(None)))
                    else ""
                )
            )
            for key, value in context.items()
            if not key.startswith("_")  # Skip private context vars
        }

    def render_safe(
        self, template_name: str, context: dict[str, Any]
    ) -> tuple[str, RenderError | None]:
        """Safe template rendering that captures errors and returns structured error information.

        Args:
            template_name: Name of the template to render
            context: Template context variables

        Returns:
            Tuple of (rendered_content, error_info)
            - If successful: (content, None)
            - If failed: ("", RenderError)
        """
        # Create a copy to avoid mutating the original context
        template_context = context.copy()
        template_context.setdefault("debug_mode", self.debug_mode)

        try:
            template = self.env.get_template(template_name)
            rendered = template.render(**template_context)
            return rendered, None

        except FileNotFoundError as e:  # Add specific handling
            error = TemplateErrorDetail(
                error_type="TemplateFileNotFound",
                message=f"Template '{template_name}' not found",
                template_name=template_name,
                context_data=self._extract_context_types(template_context),
            )
            return "", RenderError(error=error)
        except TemplateNotFound as e:  # Jinja2 specific
            error = TemplateErrorDetail(
                error_type="TemplateNotFound", 
                message=str(e),
                macro_name=None,
                template_name=template_name,
                line_number=getattr(e, "lineno", None),
                context_data=self._extract_context_types(template_context),
            )
            return "", RenderError(error=error)
        except UndefinedError as e:
            error = TemplateErrorDetail(
                error_type="UndefinedVariable",
                message=str(e),
                template_name=template_name,
                macro_name=None,
                line_number=getattr(e, "lineno", None),
                context_data=self._extract_context_types(template_context),
                stack_trace=traceback.format_exc().splitlines(),
            )
            return "", RenderError(error=error)

        except TemplateSyntaxError as e:
            error = TemplateErrorDetail(
                error_type="TemplateSyntaxError",
                message=str(e),
                template_name=template_name,
                macro_name=None,
                line_number=getattr(e, "lineno", None),
                context_data=self._extract_context_types(template_context),
                stack_trace=traceback.format_exc().splitlines(),
            )
            return "", RenderError(error=error)

        except TemplateError as e:
            error = TemplateErrorDetail(
                error_type="TemplateError",
                message=str(e),
                template_name=template_name,
                line_number=getattr(e, "lineno", None),
                context_data=self._extract_context_types(template_context),
                stack_trace=traceback.format_exc().splitlines(),
            )
            return "", RenderError(error=error)

        except Exception as e:
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=template_name,
                context_data=self._extract_context_types(template_context),
                stack_trace=traceback.format_exc().splitlines(),
            )
            return "", RenderError(error=error)

    def safe_macro(
        self, template_name: str, macro_name: str, context: dict[str, Any]
    ) -> tuple[str, RenderError | None]:
        """Safe macro rendering that captures errors and returns structured error information.

        Args:
            template_name: Name of the template containing the macro
            macro_name: Name of the macro to render
            context: Template context variables

        Returns:
            Tuple of (rendered_content, error_info)
            - If successful: (content, None)
            - If failed: ("", RenderError)
        """
        # Create a copy to avoid mutating the original context
        template_context = context.copy()
        template_context.setdefault("debug_mode", self.debug_mode)

        try:
            template = self.env.get_template(template_name)

            # Get the macro from template
            if not hasattr(template.module, macro_name):
                error = TemplateErrorDetail(
                    error_type="MacroNotFound",
                    message=f"Macro '{macro_name}' not found in template '{template_name}'",
                    template_name=template_name,
                    macro_name=macro_name,
                    context_data=self._extract_context_types(template_context),
                )
                return "", RenderError(error=error)

            macro = getattr(template.module, macro_name)

            # Call the macro with context (pass as keyword arguments)
            rendered = macro(**template_context)
            return str(rendered), None

        except UndefinedError as e:
            error = TemplateErrorDetail(
                error_type="UndefinedVariable",
                message=str(e),
                template_name=template_name,
                macro_name=macro_name,
                context_data=self._extract_context_types(template_context),
                stack_trace=traceback.format_exc().splitlines(),
            )
            return "", RenderError(error=error)

        except TemplateError as e:
            error = TemplateErrorDetail(
                error_type="TemplateError",
                message=str(e),
                template_name=template_name,
                macro_name=macro_name,
                line_number=getattr(e, "lineno", None),
                context_data=self._extract_context_types(template_context),
                stack_trace=traceback.format_exc().splitlines(),
            )
            return "", RenderError(error=error)
        
        except TypeError as e:
            # Convert TypeError to MacroNotFound if it's about missing macro
            if "arguments" in str(e).lower() or "unexpected keyword" in str(e).lower():
                error = TemplateErrorDetail(
                    error_type="MacroArgumentError",
                    message=f"Macro '{macro_name}' called with wrong arguments: {e}",
                    template_name=template_name,
                    macro_name=macro_name,
                    context_data=self._extract_context_types(template_context),
                )
                return "", RenderError(error=error)
            raise

        except Exception as e:
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=template_name,
                macro_name=macro_name,
                context_data=self._extract_context_types(template_context),
                stack_trace=traceback.format_exc().splitlines(),
            )
            return "", RenderError(error=error)

    def render_obj(
        self,
        obj: Any,
        context: dict[str, Any],
        *,
        model: type | None = None,
        variation: EnumStr | None = None,
    ) -> tuple[str, RenderError | None]:
        """Render an object using registry-based template/macro resolution.

        Args:
            obj: Object to render
            context: Template context variables
            model: Optional model type for more specific template selection
            variation: Optional variation for even more specific template selection

        Returns:
            Tuple of (rendered_content, error_info)
            - If successful: (content, None)
            - If failed: ("", RenderError)
        """
        mapping = self.registry.find_template(obj, model, variation)

        if not mapping:
            error = TemplateErrorDetail(
                error_type="TemplateNotFound",
                message=f"No template found for {type(obj).__name__} with model={model} variation={variation}",
                context_data=self._extract_context_types(context),
                stack_trace=traceback.format_exc().splitlines(),
            )
            return "", RenderError(error=error)

        # Add the object to context copy to avoid mutation
        render_context = context.copy()
        render_context.setdefault("object", obj)

        # Dispatch based on mapping type
        if mapping["type"] == "macro":
            return self.safe_macro(
                mapping["template"], mapping["macro"], render_context
            )
        return self.render_safe(mapping["path"], render_context)

    def set_debug_mode(self, debug: bool = True) -> None:
        """Enable or disable debug mode for enhanced error reporting.

        Args:
            debug: Whether to enable debug mode
        """
        self.debug_mode = debug
        self.env.globals["debug_mode"] = debug


# Usage example:
# registry = SmartTemplateRegistry()
# registry.register(User, template_name="user/profile.html", macro_name="render_user")
# templates = SmartTemplates(directory="templates", registry=registry)
# content, error = templates.render_obj(user_instance, {"request": request})
