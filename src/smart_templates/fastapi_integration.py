"""FastAPI integration for SmartTemplates."""

from __future__ import annotations

import asyncio
import logging
import traceback
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any

from pydantic import BaseModel

from .core import RenderError, SmartTemplateRegistry, SmartTemplates

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
        *,
        registry: SmartTemplateRegistry | None = None,
        debug_mode: bool = False,
        api_path_prefix: str = "/api/",
        **kwargs: Any,
    ) -> None:
        """
        Initialize SmartFastApiTemplates.

        Args:
            directory: Template directory path
            registry: Template registry instance
            debug_mode: Enable debug mode for enhanced error reporting
            api_path_prefix: URL prefix that indicates API requests (for content negotiation)
            **kwargs: Additional Jinja2 environment options
        """
        super().__init__(directory, registry=registry, debug_mode=debug_mode, **kwargs)
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.api_path_prefix = api_path_prefix

    def prepare_context(
        self, data: BaseModel | dict[str, Any] | Any, request: Request
    ) -> dict[str, Any]:
        """
        Convert function return data into a template context dictionary with FastAPI Request.

        Args:
            data: Function return value to convert to template context
            request: FastAPI Request object

        Returns:
            Dictionary suitable for template rendering
        """
        if isinstance(data, BaseModel):
            if hasattr(data, "to_template_dict"):
                context = data.to_template_dict()
            else:
                context = data.model_dump()
        elif isinstance(data, dict):
            context = data.copy()
        else:
            context = {"data": data}

        # Add FastAPI-specific context
        context.setdefault("request", request)
        context.setdefault("current_time", datetime.now())

        return context

    def _wants_json_response(self, request: Request) -> bool:
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

    def create_fallback_error_html(
        self, *, error: RenderError | None = None, message: str = "An error occurred"
    ) -> str:
        """
        Create a basic HTML error page when template rendering fails.

        Args:
            error: Optional RenderError with detailed information
            message: Fallback error message

        Returns:
            HTML error page content
        """
        if self.debug_mode and error:
            stack_trace = "\n".join(error.error.stack_trace or [])
            return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Template Error</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; }}
        .error-container {{ max-width: 800px; }}
        .error-type {{ color: #d73a49; font-weight: bold; }}
        .stack-trace {{ background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px;
                       padding: 16px; overflow-x: auto; white-space: pre; font-family: monospace; }}
        .metadata {{ background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px;
                    padding: 12px; margin: 16px 0; }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>Template Rendering Error</h1>
        <div class="metadata">
            <p><strong>Type:</strong> <span class="error-type">{error.error.error_type}</span></p>
            <p><strong>Message:</strong> {error.error.message}</p>
            <p><strong>Template:</strong> {error.error.template_name or 'Unknown'}</p>
            {f'<p><strong>Macro:</strong> {error.error.macro_name}</p>' if error.error.macro_name else ''}
            <p><strong>Timestamp:</strong> {error.error.timestamp.isoformat()}</p>
        </div>
        <h2>Stack Trace</h2>
        <div class="stack-trace">{stack_trace}</div>
    </div>
</body>
</html>"""
        else:
            display_message = (
                message
                if self.debug_mode
                else "An error occurred while processing your request."
            )
            return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Server Error</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               margin: 40px; text-align: center; color: #586069; }}
        .error-container {{ max-width: 600px; margin: 0 auto; }}
        h1 {{ color: #24292e; }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>Server Error</h1>
        <p>{display_message}</p>
    </div>
</body>
</html>"""


def create_smart_response(templates_instance: SmartFastApiTemplates) -> Callable:
    """
    Factory function that creates a smart_response decorator bound to a SmartFastApiTemplates instance.

    Args:
        templates_instance: SmartFastApiTemplates instance to use for rendering

    Returns:
        Decorator function for automatic content negotiation
    """

    def smart_response(
        template_name: str, *, error_template: str = "error.html"
    ) -> Callable:
        """
        Decorator that automatically renders templates for HTML requests and returns JSON for API requests.

        Args:
            template_name: Template file name to render for HTML responses
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
                    if templates_instance._wants_json_response(request):
                        # Return JSON response
                        if isinstance(data, BaseModel):
                            return JSONResponse(content=data.model_dump())
                        else:
                            return JSONResponse(content=data)

                    else:
                        # Prepare template context with FastAPI-specific handling
                        template_context = templates_instance.prepare_context(
                            data, request
                        )

                        # Render template
                        content, render_error = templates_instance.render_safe(
                            template_name, template_context
                        )

                        if render_error:
                            # Try to render error template
                            error_context = templates_instance.prepare_context(
                                {
                                    "error": render_error,
                                    "original_context": template_context,
                                    "debug_mode": templates_instance.debug_mode,
                                },
                                request,
                            )

                            error_content, error_render_error = (
                                templates_instance.render_safe(
                                    error_template, error_context
                                )
                            )

                            if error_render_error:
                                # Fallback to basic HTML error page
                                fallback_content = (
                                    templates_instance.create_fallback_error_html(
                                        error=render_error
                                    )
                                )
                                return HTMLResponse(
                                    content=fallback_content, status_code=500
                                )

                            return HTMLResponse(content=error_content, status_code=500)

                        return HTMLResponse(content=content)

                except Exception as e:
                    templates_instance._logger.exception(
                        "Unhandled exception in smart_response"
                    )

                    error_data = {
                        "error": {
                            "type": type(e).__name__,
                            "message": str(e),
                            "timestamp": datetime.now().isoformat(),
                        }
                    }

                    if templates_instance.debug_mode:
                        error_data["error"]["stack_trace"] = (
                            traceback.format_exc().splitlines()
                        )

                    # Return appropriate error response based on content negotiation
                    if templates_instance._wants_json_response(request):
                        return JSONResponse(status_code=500, content=error_data)
                    else:
                        error_html = templates_instance.create_fallback_error_html(
                            message=str(e)
                        )
                        return HTMLResponse(content=error_html, status_code=500)

            return wrapper

        return decorator

    return smart_response


# Usage example:
# registry = SmartTemplateRegistry()
# registry.register(User, template_name="user/profile.html", macro_name="render_user")
# templates = SmartFastApiTemplates(directory="templates", registry=registry, debug_mode=True)
# smart_response = create_smart_response(templates)
#
# @app.get("/users/{user_id}")
# @smart_response("user/profile.html")
# async def get_user(request: Request, user_id: int):
#     return {"user": get_user_by_id(user_id)}
