"""FastAPI integration for SmartTemplates - HTTP decorators and response handling."""

from __future__ import annotations

import asyncio
import logging
import warnings
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any

from jinja2 import FileSystemLoader
from pydantic import BaseModel

from .core import RenderError, RegistrationConfig, RegistrationType, SmartTemplateRegistry, SmartTemplates

try:
    from fastapi import Request
    from fastapi.responses import HTMLResponse, JSONResponse
except ImportError as e:
    raise ImportError(
        "FastAPI dependencies not installed. Install with: pip install smart-templates[fastapi]"
    ) from e


class SmartFastApiTemplates(SmartTemplates):
    """
    FastAPI-specific extension of SmartTemplates that adds HTTP request/response handling,
    content negotiation, and FastAPI-specific error formatting.
    """

    def __init__(
        self,
        directory: str,
        *,  # CRITICAL: Force keyword-only arguments
        registry: SmartTemplateRegistry | None = None,
        debug_mode: bool = False,
        api_path_prefix: str = "/api/",
        auto_reload: bool | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize SmartFastApiTemplates.

        Args:
            directory: Template directory path
            registry: Template registry instance
            debug_mode: Enable debug mode for enhanced error reporting
            api_path_prefix: URL prefix that indicates API requests (for content negotiation)
            auto_reload: Auto-reload templates on file changes (defaults to debug_mode)
            **kwargs: Additional Jinja2 environment options
        """
        # Set auto_reload based on debug_mode if not explicitly provided
        if auto_reload is None:
            auto_reload = debug_mode
            
        kwargs.setdefault("auto_reload", auto_reload)
        
        super().__init__(directory, registry=registry, debug_mode=debug_mode, **kwargs)
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.api_path_prefix = api_path_prefix
        
        # Register core error templates
        self._register_core_templates()

    def _register_core_templates(self) -> None:
        """Register core error handling templates."""
        # Add core templates directory to loader search path
        core_templates_dir = Path(__file__).parent / "templates" / "fastapi"
        
        if core_templates_dir.exists():
            # Prepend core templates to search path for fallback
            current_paths = self.env.loader.searchpath
            self.env.loader = FileSystemLoader([str(core_templates_dir)] + current_paths)
        
        # Register error handling templates
        error_config = RegistrationConfig(
            name="error.html",
            registration_type=RegistrationType.TEMPLATE,
            target="error.html"
        )
        self.registry.register(RenderError, config=error_config)

    def prepare_context(
        self, data: BaseModel | dict[str, Any] | Any, request: Request | None = None
    ) -> dict[str, Any]:
        """
        Convert function return data into a template context dictionary.

        Args:
            data: Function return value to convert to template context
            request: FastAPI Request object (deprecated - use dependency injection)

        Returns:
            Dictionary suitable for template rendering
        """
        if request is not None:
            warnings.warn(
                "Passing request to prepare_context is deprecated. "
                "Use FastAPI dependency injection instead.",
                DeprecationWarning,
                stacklevel=2
            )

        # CRITICAL: Always copy, never mutate input
        if isinstance(data, BaseModel):
            if hasattr(data, "to_template_dict"):
                template_context = data.to_template_dict()
            else:
                template_context = data.model_dump()
        elif isinstance(data, dict):
            template_context = data.copy()  # Defensive copy
        else:
            template_context = {"data": data}

        # Add framework-specific context safely
        template_context.setdefault("current_time", datetime.now())
        
        return template_context

    def wants_json_response(self, request: Request) -> bool:
        """
        Determine if the request expects a JSON response based on headers and URL.

        Args:
            request: FastAPI Request object

        Returns:
            True if JSON response is expected, False for HTML
        """
        accept_header = request.headers.get("accept", "text/html").lower()

        # Check Accept header for JSON preference
        wants_json = (
            "application/json" in accept_header
            or "application/*" in accept_header
            or accept_header == "*/*"
        )

        # Check if URL indicates API endpoint
        is_api_path = request.url.path.startswith(self.api_path_prefix)

        return wants_json or is_api_path

    def set_debug_mode(self, debug: bool = True, auto_reload: bool | None = None) -> None:
        """
        Enable or disable debug mode with template auto-reloading.
        
        Args:
            debug: Enable debug mode
            auto_reload: Enable template auto-reloading (defaults to debug value)
        """
        super().set_debug_mode(debug)
        
        if auto_reload is None:
            auto_reload = debug
            
        # Update loader for auto-reload
        if hasattr(self.env.loader, 'auto_reload'):
            self.env.loader.auto_reload = auto_reload


def create_smart_response(templates_instance: SmartFastApiTemplates) -> Callable:
    """
    Factory function that creates a smart_response decorator.

    Args:
        templates_instance: SmartFastApiTemplates instance to use for rendering

    Returns:
        Decorator function for automatic content negotiation
    """

    def smart_response(
        template_name: str | None = None, 
        *, 
        error_template: str = "error.html"
    ) -> Callable:
        """
        Decorator that automatically renders templates for HTML requests and returns JSON for API requests.

        Args:
            template_name: Template file name to render for HTML responses (None for registry-based resolution)
            error_template: Template to use for error responses

        Returns:
            Decorated function
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(
                request: Request, *args: Any, **kwargs: Any
            ) -> JSONResponse | HTMLResponse:
                try:
                    # Execute the original function
                    if asyncio.iscoroutinefunction(func):
                        data = await func(request, *args, **kwargs)
                    else:
                        data = func(request, *args, **kwargs)

                    # Determine response type based on request characteristics
                    if templates_instance.wants_json_response(request):
                        # Return JSON response
                        if isinstance(data, BaseModel):
                            return JSONResponse(content=data.model_dump())
                        else:
                            return JSONResponse(content=data)

                    else:
                        # Prepare template context (defensive copy)
                        template_context = templates_instance.prepare_context(data)
                        # CRITICAL: Make another copy before adding request to avoid mutation
                        render_context = template_context.copy()
                        render_context["request"] = request

                        # Determine which template to use
                        content = ""
                        render_error = None
                        
                        if template_name:
                            # Use explicit template
                            content, render_error = templates_instance.render_safe(
                                template_name, render_context
                            )
                        else:
                            # Use registry-based resolution (includes auto-generation if enabled)
                            content, render_error = templates_instance.render_obj(
                                data, render_context
                            )

                        if render_error:
                            # Pass render error directly to error template
                            error_context = {
                                "error": render_error,
                                "request": request,
                                "debug_mode": templates_instance.debug_mode,
                                "original_template": template_name,
                                "original_context_keys": list(render_context.keys())
                            }

                            error_content, error_render_error = (
                                templates_instance.render_safe(error_template, error_context)
                            )

                            if error_render_error:
                                # Last resort: render error as RenderError object
                                fallback_content, _ = templates_instance.render_obj(
                                    render_error, {"request": request}
                                )
                                return HTMLResponse(
                                    content=fallback_content or "Template rendering failed",
                                    status_code=500
                                )

                            return HTMLResponse(content=error_content, status_code=500)

                        return HTMLResponse(content=content)

                except Exception as e:
                    templates_instance._logger.exception(
                        "Unhandled exception in smart_response for %s", template_name or "registry-resolved"
                    )

                    # Create structured error using our BaseModel system
                    import traceback
                    from .core import TemplateErrorDetail
                    
                    error_detail = TemplateErrorDetail(
                        error_type=type(e).__name__,
                        message=str(e),
                        template_name=template_name or "registry-resolved",
                        stack_trace=traceback.format_exc().splitlines()
                    )
                    structured_error = RenderError(
                        error=error_detail,
                        debug_info={
                            "function": func.__name__,
                            "route_template": template_name or "registry-resolved"
                        }
                    )

                    # Return appropriate error response based on content negotiation
                    if templates_instance.wants_json_response(request):
                        return JSONResponse(status_code=500, content=structured_error.model_dump())
                    else:
                        error_html, _ = templates_instance.render_obj(
                            structured_error, {"request": request}
                        )
                        return HTMLResponse(
                            content=error_html or f"<h1>Error: {e}</h1>", 
                            status_code=500
                        )

            return wrapper

        return decorator

    return smart_response


# FastAPI-native patterns for advanced integration
class SmartTemplateConfig:
    """Configuration for SmartTemplates FastAPI integration."""
    
    def __init__(
        self,
        template_dir: str,
        *,
        debug_mode: bool = False,
        api_prefix: str = "/api/",
        default_error_template: str = "error.html",
        auto_reload: bool | None = None
    ):
        self.template_dir = template_dir
        self.debug_mode = debug_mode
        self.api_prefix = api_prefix
        self.default_error_template = default_error_template
        self.auto_reload = auto_reload


def create_smart_templates_dependency(config: SmartTemplateConfig) -> Callable:
    """
    Create a FastAPI dependency for SmartTemplates.
    
    Usage:
        config = SmartTemplateConfig("templates/")
        get_templates = create_smart_templates_dependency(config)
        
        @app.get("/users/{user_id}")
        async def get_user(user_id: int, templates: SmartFastApiTemplates = Depends(get_templates)):
            # Use templates instance
    """
    templates_instance = None
    
    def get_templates() -> SmartFastApiTemplates:
        nonlocal templates_instance
        if templates_instance is None:
            templates_instance = SmartFastApiTemplates(
                config.template_dir,
                debug_mode=config.debug_mode,
                api_path_prefix=config.api_prefix,
                auto_reload=config.auto_reload
            )
        return templates_instance
    
    return get_templates


# Usage examples:
# 
# # Registry-based resolution (auto-generation happens in registry)
# templates = SmartFastApiTemplates("templates/")
# smart_response = create_smart_response(templates)
#
# @app.get("/users/{user_id}")
# @smart_response()  # Registry resolves template (may auto-generate)
# async def get_user(request: Request, user_id: int):
#     return User.get(user_id)
#
# # Explicit template (existing behavior)
# @app.get("/users/{user_id}/profile")
# @smart_response("user/profile.html")
# async def get_user_profile(request: Request, user_id: int):
#     return User.get(user_id)