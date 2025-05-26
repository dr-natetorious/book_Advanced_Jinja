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
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol, Union

from jinja2 import (
    Environment,
    FileSystemLoader,
    TemplateError,
    TemplateNotFound,
    TemplateSyntaxError,
    UndefinedError,
)
from pydantic import BaseModel, Field, ConfigDict

# Type aliases and protocols
EnumStr = Union[str, Enum]


class PatternFunction(Protocol):
    """Protocol for pattern functions used in template resolution."""
    
    def __call__(
        self, obj: Any, model: type | None, variation: EnumStr | None
    ) -> dict[str, str] | None:
        """Return template mapping or None if pattern doesn't match."""
        ...


class RegistrationType(Enum):
    """Types of Jinja2 registrations supported by SmartTemplates."""
    TEMPLATE = "template"
    MACRO = "macro"
    FILTER = "filter"
    TEST = "test"
    FUNCTION = "function"


class RegistrationConfig(BaseModel):
    """Configuration for template system registration."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    name: str = Field(..., description="Name/path of the registration target")
    registration_type: RegistrationType = Field(..., description="Type of Jinja2 registration")
    target: str = Field(..., description="Target identifier (template path, function name, etc.)")
    
    # Optional refinements for template resolution
    model_class: type | None = Field(None, description="Model type for specific mapping")
    variation: EnumStr | None = Field(None, description="Variation for specific mapping")


class TemplateErrorDetail(BaseModel):
    """Detailed information about template rendering errors."""
    model_config = ConfigDict(frozen=True)

    error_type: str = Field(..., description="Type of error that occurred")
    message: str = Field(..., description="Human-readable error message")
    template_name: str | None = Field(None, description="Name of the template that caused the error")
    macro_name: str | None = Field(None, description="Name of the macro that caused the error")
    line_number: int | None = Field(None, description="Line number where the error occurred")
    context_data: dict[str, str] | None = Field(None, description="Context variable types for debugging")
    stack_trace: list[str] | None = Field(None, description="Full stack trace of the error")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the error occurred")


class RenderError(BaseModel):
    """Structured error response for template rendering failures."""
    model_config = ConfigDict(frozen=True)

    success: bool = Field(False, description="Whether the operation was successful")
    error: TemplateErrorDetail = Field(..., description="Detailed error information")
    debug_info: dict[str, Any] | None = Field(None, description="Additional debug information")


class SmartTemplateRegistry:
    """Registry for mapping objects to templates and macros based on type, model, and variation."""

    def __init__(self) -> None:
        self._registrations: dict[str, RegistrationConfig] = {}
        self._patterns: list[PatternFunction] = []
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def register(
        self,
        obj_type: type,
        *,
        config: RegistrationConfig,
    ) -> None:
        """Register a template/macro/filter/etc. for an object type.

        Args:
            obj_type: The object type to register
            config: Registration configuration specifying type and target
        """
        key = self._make_key(obj_type, config.model_class, config.variation)
        self._registrations[key] = config
        
        # Clear cache when registrations change
        self._find_template_cached.cache_clear()

    def register_simple(
        self,
        obj_type: type,
        *,
        template_name: str | None = None,
        macro_name: str | None = None,
        model: type | None = None,
        variation: EnumStr | None = None,
    ) -> None:
        """Simplified registration for backward compatibility and common cases."""
        if not template_name and not macro_name:
            raise ValueError(
                f"Registration for {obj_type.__name__} requires either template_name or macro_name"
            )
        
        if template_name and macro_name:
            # Register macro with explicit template
            config = RegistrationConfig(
                name=macro_name,
                registration_type=RegistrationType.MACRO,
                target=template_name,
                model_class=model,
                variation=variation
            )
        elif macro_name:
            # Register macro with convention-based template
            config = RegistrationConfig(
                name=macro_name,
                registration_type=RegistrationType.MACRO,
                target=self._convention_based_name(obj_type, model, variation),
                model_class=model,
                variation=variation
            )
        else:
            # Register template
            config = RegistrationConfig(
                name=template_name,
                registration_type=RegistrationType.TEMPLATE,
                target=template_name,
                model_class=model,
                variation=variation
            )
        
        self.register(obj_type, config=config)

    def unregister(
        self, 
        obj_type: type, 
        *,
        model: type | None = None, 
        variation: EnumStr | None = None
    ) -> bool:
        """Remove a registration."""
        key = self._make_key(obj_type, model, variation)
        removed = self._registrations.pop(key, None) is not None
        
        if removed:
            self._find_template_cached.cache_clear()
            
        return removed

    def clear(self) -> None:
        """Clear all registrations and patterns."""
        self._registrations.clear()
        self._patterns.clear()
        self._find_template_cached.cache_clear()

    def list_registrations(self) -> dict[str, RegistrationConfig]:
        """Return all registrations for debugging."""
        return self._registrations.copy()

    def register_pattern(self, pattern_func: PatternFunction) -> None:
        """Register a pattern function for dynamic template resolution."""
        self._patterns.append(pattern_func)

    def find_template(
        self, obj: Any, model: type | None = None, variation: EnumStr | None = None
        ) -> dict[str, str] | None:
        """Find template/macro mapping for an object."""
        obj_type = type(obj)
        
        # Convert to strings for caching
        model_name = model.__name__ if model else None
        variation_str = variation.value if isinstance(variation, Enum) else str(variation) if variation else None
        
        # Try cached lookup first (registrations only)
        result = self._find_template_cached(obj_type.__name__, model_name, variation_str)
        if result:
            return result
        
        # Try pattern functions (need actual obj)
        for pattern_func in self._patterns:
            try:
                result = pattern_func(obj, model, variation)
                if result:
                    return result
            except Exception as e:
                self._logger.warning("Pattern function failed: %s", e)
        
        # Convention-based fallback
        return {
            "type": "template",
            "path": self._convention_based_name_from_strings(obj_type.__name__, model_name, variation_str),
        }

    @lru_cache(maxsize=256)
    def _find_template_cached(
        self, 
        obj_type_name: str, 
        model_name: str | None, 
        variation_str: str | None,
        ) -> dict[str, str] | None:
        """Cached template lookup implementation."""
        # Try exact matches with fallback hierarchy
        for key_parts in [
            (obj_type_name, model_name, variation_str),
            (obj_type_name, model_name, None),
            (obj_type_name, None, variation_str),
            (obj_type_name, None, None),
        ]:
            key = ":".join(filter(None, key_parts))
            if key in self._registrations:
                config = self._registrations[key]
                
                if config.registration_type == RegistrationType.MACRO:
                    return {
                        "type": "macro",
                        "template": config.target,
                        "macro": config.name,
                    }
                elif config.registration_type == RegistrationType.TEMPLATE:
                    return {
                        "type": "template",
                        "path": config.target,
                    }
        
        # No registration found
        return None

    def debug_lookup(
        self, obj: Any, model: type | None = None, variation: EnumStr | None = None
    ) -> dict[str, Any]:
        """Return detailed lookup information for debugging."""
        obj_type = type(obj)
        
        tried_keys = []
        for key_parts in [
            (obj_type, model, variation),
            (obj_type, model, None),
            (obj_type, None, variation),
            (obj_type, None, None),
        ]:
            key = self._make_key(*key_parts)
            registration = self._registrations.get(key)
            tried_keys.append({
                "key": key,
                "found": key in self._registrations,
                "registration": registration.model_dump() if registration else None
            })
        
        final_mapping = self.find_template(obj, model, variation)
        
        return {
            "obj_type": obj_type.__name__,
            "model": model.__name__ if model else None,
            "variation": str(variation) if variation else None,
            "lookup_hierarchy": tried_keys,
            "pattern_functions_count": len(self._patterns),
            "final_mapping": final_mapping,
            "cache_info": self._find_template_cached.cache_info()._asdict(),
        }

    def _make_key(
        self, obj_type: type, model: type | None, variation: EnumStr | None
    ) -> str:
        """Create lookup key for registration mapping."""
        parts = [obj_type.__name__]
        if model:
            parts.append(model.__name__)
        if variation:
            parts.append(str(variation))
        return ":".join(parts)

    def _convention_based_name(
        self, obj_type: type, model: type | None, variation: EnumStr | None
    ) -> str:
        """Generate template name based on naming conventions."""
        return self._convention_based_name_from_strings(
            obj_type.__name__,
            model.__name__ if model else None,
            str(variation) if variation else None
        )
        
    def _convention_based_name_from_strings(
        self, obj_type_name: str, model_name: str | None, variation_str: str | None
    ) -> str:
        """Generate template name from string components."""
        # Convert CamelCase to snake_case
        snake_case = ""
        for i, c in enumerate(obj_type_name):
            if c.isupper() and i > 0:
                snake_case += "_"
            snake_case += c.lower()

        parts = [snake_case]
        if model_name:
            model_snake = ""
            for i, c in enumerate(model_name):
                if c.isupper() and i > 0:
                    model_snake += "_"
                model_snake += c.lower()
            parts.append(model_snake)
        if variation_str:
            parts.append(variation_str.lower())

        return f"{'/'.join(parts)}.html"

    def __repr__(self) -> str:
        return (
            f"SmartTemplateRegistry("
            f"registrations={len(self._registrations)}, "
            f"patterns={len(self._patterns)}, "
            f"cache={self._find_template_cached.cache_info().hits}/{self._find_template_cached.cache_info().currsize}"
            f")"
        )


class SmartTemplates:
    """Enhanced template engine with error handling, object-based template resolution, and macro support."""

    def __init__(
        self,
        directory: str,
        registry: SmartTemplateRegistry | None = None,
        *,
        debug_mode: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize the template engine."""
        # Validate template directory
        template_path = Path(directory)
        if not template_path.exists():
            raise ValueError(f"Template directory '{directory}' does not exist")
        if not template_path.is_dir():
            raise ValueError(f"Template path '{directory}' is not a directory")

        # Create Jinja2 environment
        loader = FileSystemLoader(directory)
        self.env = Environment(loader=loader, **kwargs)
        self.registry = registry or SmartTemplateRegistry()
        self.debug_mode = debug_mode
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Add debugging helpers to template globals
        self.env.globals.update({
            "debug_var": self._debug_variable,
            "safe_get": self._safe_get,
            "debug_mode": self.debug_mode,
        })

    def _debug_variable(self, var: Any, var_name: str = "unknown") -> Any:
        """Helper function available in templates for debugging variables."""
        if self.debug_mode:
            self._logger.info("DEBUG %s: %s = %r", var_name, type(var).__name__, var)
        return var

    def _safe_get(self, obj: Any, key: str | int, default: Any = None) -> Any:
        """Safe attribute/key access helper for templates."""
        try:
            if isinstance(key, int) and hasattr(obj, "__getitem__"):
                return obj[key]
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
            if not key.startswith("_")
        }

    def render_safe(
        self, template_name: str, context: dict[str, Any]
    ) -> tuple[str, RenderError | None]:
        """Safe template rendering that captures errors and returns structured error information."""
        # Always copy context to avoid mutation
        template_context = context.copy()
        template_context.setdefault("debug_mode", self.debug_mode)

        try:
            template = self.env.get_template(template_name)
            rendered = template.render(**template_context)
            return rendered, None

        except TemplateNotFound as e:
            error = TemplateErrorDetail(
                error_type="TemplateNotFound",
                message=f"Template '{template_name}' not found in template directory",
                template_name=template_name,
                context_data=self._extract_context_types(template_context),
            )
            return "", RenderError(error=error)

        except UndefinedError as e:
            error = TemplateErrorDetail(
                error_type="UndefinedVariable",
                message=str(e),
                template_name=template_name,
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
        """Safe macro rendering that captures errors and returns structured error information."""
        template_context = context.copy()
        template_context.setdefault("debug_mode", self.debug_mode)

        try:
            template = self.env.get_template(template_name)

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
        """Render an object using registry-based template/macro resolution."""
        mapping = self.registry.find_template(obj, model, variation)

        if not mapping:
            error = TemplateErrorDetail(
                error_type="TemplateNotFound",
                message=f"No template found for {type(obj).__name__} with model={model} variation={variation}",
                context_data=self._extract_context_types(context),
                stack_trace=traceback.format_exc().splitlines(),
            )
            return "", RenderError(error=error)

        # Copy context to avoid mutation
        render_context = context.copy()
        render_context.setdefault("object", obj)

        # Dispatch based on mapping type
        if mapping["type"] == "macro":
            return self.safe_macro(mapping["template"], mapping["macro"], render_context)
        return self.render_safe(mapping["path"], render_context)

    def debug_render_obj(
        self,
        obj: Any,
        context: dict[str, Any],
        *,
        model: type | None = None,
        variation: EnumStr | None = None,
    ) -> dict[str, Any]:
        """Debug version of render_obj that returns detailed resolution information."""
        lookup_debug = self.registry.debug_lookup(obj, model, variation)
        content, error = self.render_obj(obj, context, model=model, variation=variation)
        
        return {
            "lookup_debug": lookup_debug,
            "render_success": error is None,
            "render_error": error.model_dump() if error else None,
            "content_length": len(content) if content else 0,
            "context_keys": list(context.keys()),
        }

    def set_debug_mode(self, debug: bool = True) -> None:
        """Enable or disable debug mode for enhanced error reporting."""
        self.debug_mode = debug
        self.env.globals["debug_mode"] = debug

    def __repr__(self) -> str:
        template_dir = self.env.loader.searchpath[0] if self.env.loader.searchpath else "unknown"
        return (
            f"SmartTemplates("
            f"directory='{template_dir}', "
            f"debug_mode={self.debug_mode}, "
            f"registry={repr(self.registry)}"
            f")"
        )