from jinja2 import Environment, FileSystemLoader, TemplateError, UndefinedError, TemplateSyntaxError
from pydantic import BaseModel
from typing import Dict, Any, Optional, List, Union, Type, Callable
from enum import Enum
import traceback
import logging
import asyncio
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

# Type aliases
EnumStr = Union[str, Enum]

# Error models
class TemplateErrorDetail(BaseModel):
    error_type: str
    message: str
    template_name: Optional[str] = None
    macro_name: Optional[str] = None
    line_number: Optional[int] = None
    context_data: Optional[Dict[str, str]] = None
    stack_trace: Optional[List[str]] = None
    timestamp: datetime = datetime.now()

class RenderError(BaseModel):
    success: bool = False
    error: TemplateErrorDetail
    debug_info: Optional[Dict[str, Any]] = None

# Template registry for object-based template resolution
class SmartTemplateRegistry:
    """Registry for mapping objects to templates and macros based on type, model, and variation."""
    
    def __init__(self):
        self._mappings: Dict[str, Dict[str, str]] = {}
        self._patterns: List[Callable] = []
        
    def register(self, obj_type: Type, template_name: str = None, macro_name: str = None, 
                 model: Optional[Type] = None, variation: Optional[EnumStr] = None):
        """Register a specific object type to template/macro mapping"""
        key = self._make_key(obj_type, model, variation)
        mapping = {}
        if template_name:
            mapping["template"] = template_name
        if macro_name:
            mapping["macro"] = macro_name
        self._mappings[key] = mapping
        
    def register_pattern(self, pattern_func: Callable):
        """Register a pattern function for dynamic template resolution"""
        self._patterns.append(pattern_func)
        
    def find_template(self, obj: Any, model: Optional[Type] = None, variation: Optional[EnumStr] = None) -> Optional[Dict[str, str]]:
        """
        Find template/macro mapping for an object.
        Returns: {"type": "template", "path": "..."} or {"type": "macro", "template": "...", "macro": "..."}
        """
        obj_type = type(obj)
        
        # Try exact matches first
        for key_parts in [
            (obj_type, model, variation),
            (obj_type, model, None),
            (obj_type, None, variation),
            (obj_type, None, None)
        ]:
            key = self._make_key(*key_parts)
            if key in self._mappings:
                mapping = self._mappings[key]
                if "macro" in mapping:
                    return {
                        "type": "macro",
                        "template": mapping.get("template", self._convention_based_name(obj_type, model, variation)),
                        "macro": mapping["macro"]
                    }
                else:
                    return {
                        "type": "template", 
                        "path": mapping.get("template", self._convention_based_name(obj_type, model, variation))
                    }
        
        # Try pattern functions
        for pattern_func in self._patterns:
            try:
                result = pattern_func(obj, model, variation)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Pattern function failed: {e}")
                
        # Convention-based fallback (template)
        return {
            "type": "template",
            "path": self._convention_based_name(obj_type, model, variation)
        }
        
    def _make_key(self, obj_type: Type, model: Optional[Type], variation: Optional[EnumStr]) -> str:
        """Create lookup key for template mapping"""
        parts = [obj_type.__name__]
        if model:
            parts.append(model.__name__)
        if variation:
            parts.append(str(variation))
        return ":".join(parts)
        
    def _convention_based_name(self, obj_type: Type, model: Optional[Type], variation: Optional[EnumStr]) -> str:
        """Generate template name based on naming conventions"""
        # Convert CamelCase to snake_case
        name = obj_type.__name__
        snake_case = "".join(["_" + c.lower() if c.isupper() and i > 0 else c.lower() 
                             for i, c in enumerate(name)])
        
        parts = [snake_case]
        if model:
            model_name = "".join(["_" + c.lower() if c.isupper() and i > 0 else c.lower() 
                                 for i, c in enumerate(model.__name__)])
            parts.append(model_name)
        if variation:
            parts.append(str(variation).lower())
            
        return f"{'/'.join(parts)}.html"

# Core SmartTemplates - framework agnostic
class SmartTemplates:
    """
    Enhanced template engine with error handling, object-based template resolution,
    and macro support. Framework agnostic - can be used with any Python application.
    """
    
    def __init__(self, directory: str, registry: Optional[SmartTemplateRegistry] = None, **kwargs):
        # Create Jinja2 environment
        loader = FileSystemLoader(directory) if isinstance(directory, str) else FileSystemLoader(directory)
        self.env = Environment(loader=loader, **kwargs)
        
        self.registry = registry or SmartTemplateRegistry()
        self.debug_mode = False
        
        # Add debugging helpers to template globals
        self.env.globals.update({
            'debug_var': self._debug_variable,
            'safe_get': self._safe_get,
            'debug_mode': False
        })
        
    def _debug_variable(self, var: Any, var_name: str = "unknown") -> Any:
        """Helper function available in templates for debugging variables"""
        if self.env.globals.get('debug_mode', False):
            logger.info(f"DEBUG {var_name}: {type(var).__name__} = {repr(var)}")
        return var
    
    def _safe_get(self, obj: Any, key: str, default: Any = None) -> Any:
        """Safe attribute/key access helper for templates"""
        try:
            if hasattr(obj, key):
                return getattr(obj, key)
            elif isinstance(obj, dict) and key in obj:
                return obj[key]
            elif hasattr(obj, '__getitem__'):
                return obj[key]
            else:
                return default
        except (KeyError, AttributeError, TypeError):
            return default
    
    def _extract_context_types(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Extract type information from context for debugging"""
        return {
            key: f"{type(value).__name__}" + (
                f"[{len(value)}]" if hasattr(value, '__len__') and not isinstance(value, str)
                else f"({value})" if isinstance(value, (int, float, bool, type(None)))
                else ""
            )
            for key, value in context.items()
            if not key.startswith("_")  # Skip private context vars
        }
    
    def render_safe(self, template_name: str, context: Dict[str, Any]) -> tuple[str, Optional[RenderError]]:
        """Safe template rendering that captures errors and returns structured error information."""
        try:
            if 'debug_mode' not in context:
                context['debug_mode'] = self.debug_mode
            
            template = self.env.get_template(template_name)
            rendered = template.render(**context)
            return rendered, None
            
        except UndefinedError as e:
            error = TemplateErrorDetail(
                error_type="UndefinedVariable",
                message=str(e),
                template_name=template_name,
                context_data=self._extract_context_types(context),
                stack_trace=traceback.format_exc().splitlines()
            )
            return "", RenderError(error=error)
            
        except TemplateSyntaxError as e:
            error = TemplateErrorDetail(
                error_type="TemplateSyntaxError",
                message=str(e),
                template_name=template_name,
                line_number=getattr(e, 'lineno', None),
                context_data=self._extract_context_types(context),
                stack_trace=traceback.format_exc().splitlines()
            )
            return "", RenderError(error=error)
            
        except TemplateError as e:
            error = TemplateErrorDetail(
                error_type="TemplateError",
                message=str(e),
                template_name=template_name,
                line_number=getattr(e, 'lineno', None),
                context_data=self._extract_context_types(context),
                stack_trace=traceback.format_exc().splitlines()
            )
            return "", RenderError(error=error)
            
        except Exception as e:
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=template_name,
                context_data=self._extract_context_types(context),
                stack_trace=traceback.format_exc().splitlines()
            )
            return "", RenderError(error=error)
    
    def safe_macro(self, template_name: str, macro_name: str, context: Dict[str, Any]) -> tuple[str, Optional[RenderError]]:
        """Safe macro rendering that captures errors and returns structured error information."""
        try:
            if 'debug_mode' not in context:
                context['debug_mode'] = self.debug_mode
            
            template = self.env.get_template(template_name)
            
            # Get the macro from template
            if not hasattr(template.module, macro_name):
                error = TemplateErrorDetail(
                    error_type="MacroNotFound",
                    message=f"Macro '{macro_name}' not found in template '{template_name}'",
                    template_name=template_name,
                    macro_name=macro_name,
                    context_data=self._extract_context_types(context)
                )
                return "", RenderError(error=error)
            
            macro = getattr(template.module, macro_name)
            
            # Call the macro with context (pass as keyword arguments)
            rendered = macro(**context)
            return str(rendered), None
            
        except UndefinedError as e:
            error = TemplateErrorDetail(
                error_type="UndefinedVariable",
                message=str(e),
                template_name=template_name,
                macro_name=macro_name,
                context_data=self._extract_context_types(context),
                stack_trace=traceback.format_exc().splitlines()
            )
            return "", RenderError(error=error)
            
        except TemplateError as e:
            error = TemplateErrorDetail(
                error_type="TemplateError",
                message=str(e),
                template_name=template_name,
                macro_name=macro_name,
                line_number=getattr(e, 'lineno', None),
                context_data=self._extract_context_types(context),
                stack_trace=traceback.format_exc().splitlines()
            )
            return "", RenderError(error=error)
            
        except Exception as e:
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=template_name,
                macro_name=macro_name,
                context_data=self._extract_context_types(context),
                stack_trace=traceback.format_exc().splitlines()
            )
            return "", RenderError(error=error)
    
    def render_obj(self, obj: Any, context: Dict[str, Any], model: Optional[Type] = None, variation: Optional[EnumStr] = None) -> tuple[str, Optional[RenderError]]:
        """Render an object using registry-based template/macro resolution."""
        mapping = self.registry.find_template(obj, model, variation)
        
        if not mapping:
            error = TemplateErrorDetail(
                error_type="TemplateNotFound",
                message=f"No template found for {type(obj).__name__} with model={model} variation={variation}",
                context_data=self._extract_context_types(context),
                stack_trace=traceback.format_exc().splitlines()
            )
            return "", RenderError(error=error)
        
        # Add the object to context if not already present
        if 'object' not in context:
            context['object'] = obj
            
        # Dispatch based on mapping type
        if mapping["type"] == "macro":
            return self.safe_macro(mapping["template"], mapping["macro"], context)
        else:
            return self.render_safe(mapping["path"], context)
    
    def set_debug_mode(self, debug: bool = True):
        """Enable or disable debug mode for enhanced error reporting"""
        self.debug_mode = debug
        self.env.globals['debug_mode'] = debug

# FastAPI-specific subclass
class SmartFastApiTemplates(SmartTemplates):
    """
    FastAPI-specific extension of SmartTemplates that adds HTTP request/response handling,
    content negotiation, and FastAPI-specific error formatting.
    """
    
    def __init__(self, directory: str, registry: Optional[SmartTemplateRegistry] = None, **kwargs):
        super().__init__(directory, registry, **kwargs)
    
    def TemplateResponse(self, name: str, context: dict):
        return HTMLResponse(self.env.get_template(name).render(context))

    def prepare_context(self, data: Union[BaseModel, Dict[str, Any]], request: Any) -> Dict[str, Any]:
        """Convert function return data into a template context dictionary with FastAPI Request."""
        if isinstance(data, BaseModel):
            if hasattr(data, 'to_template_dict'):
                context = data.to_template_dict()
            else:
                context = data.model_dump()
        elif isinstance(data, dict):
            context = data.copy()
        else:
            context = {"data": data}
        
        # Add FastAPI-specific context
        context["request"] = request
        context["current_time"] = datetime.now()
        
        return context
    
    def create_fallback_error_html(self, error: Optional[RenderError], message: str = "An error occurred") -> str:
        """Create a basic HTML error page when template rendering fails"""
        if self.debug_mode and error:
            return f"""
            <!DOCTYPE html>
            <html>
            <head><title>Template Error</title></head>
            <body>
                <h1>Template Rendering Error</h1>
                <p><strong>Type:</strong> {error.error.error_type}</p>
                <p><strong>Message:</strong> {error.error.message}</p>
                <p><strong>Template:</strong> {error.error.template_name or 'Unknown'}</p>
                {f'<p><strong>Macro:</strong> {error.error.macro_name}</p>' if error.error.macro_name else ''}
                <pre style="background: #f5f5f5; padding: 10px; overflow-x: auto;">
{chr(10).join(error.error.stack_trace or [])}
                </pre>
            </body>
            </html>
            """
        else:
            return f"""
            <!DOCTYPE html>
            <html>
            <head><title>Server Error</title></head>
            <body>
                <h1>Server Error</h1>
                <p>{message if self.debug_mode else 'An error occurred while processing your request.'}</p>
            </body>
            </html>
            """

def create_smart_response(templates_instance: SmartFastApiTemplates):
    """Factory function that creates a smart_response decorator bound to a SmartFastApiTemplates instance."""
    
    def smart_response(template_name: str, error_template: str = "error.html"):
        """Decorator that automatically renders templates for HTML requests and returns JSON for API requests."""
        
        def decorator(func):
            @wraps(func)
            async def wrapper(request, *args, **kwargs):
                try:
                    # Execute the original function
                    if asyncio.iscoroutinefunction(func):
                        data = await func(request, *args, **kwargs)
                    else:
                        data = func(request, *args, **kwargs)
                    
                    # Determine response type based on Accept header
                    accept_header = request.headers.get("accept", "text/html").lower()
                    wants_json = (
                        "application/json" in accept_header or
                        "application/*" in accept_header or
                        request.url.path.startswith("/api/")
                    )
                    
                    if wants_json:
                        # Import here to avoid circular imports
                        from fastapi.responses import JSONResponse
                        
                        if isinstance(data, BaseModel):
                            return JSONResponse(content=data.model_dump())
                        else:
                            return JSONResponse(content=data)
                    
                    else:
                        # Import here to avoid circular imports
                        from fastapi.responses import HTMLResponse
                        
                        # Prepare template context with FastAPI-specific handling
                        context = templates_instance.prepare_context(data, request)
                        
                        # Render template
                        content, error = templates_instance.render_safe(template_name, context)
                        
                        if error:
                            # Try to render error template
                            error_context = {
                                "request": request,
                                "error": error,
                                "original_context": context,
                                "debug_mode": templates_instance.debug_mode
                            }
                            
                            error_content, error_render_error = templates_instance.render_safe(error_template, error_context)
                            
                            if error_render_error:
                                return HTMLResponse(
                                    content=templates_instance.create_fallback_error_html(error),
                                    status_code=500
                                )
                            
                            return HTMLResponse(content=error_content, status_code=500)
                        
                        return HTMLResponse(content=content)
                    
                except Exception as e:
                    # Import here to avoid circular imports
                    from fastapi.responses import JSONResponse, HTMLResponse
                    
                    error_data = {
                        "error": {
                            "type": type(e).__name__,
                            "message": str(e),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    if templates_instance.debug_mode:
                        error_data["error"]["stack_trace"] = traceback.format_exc().splitlines()
                    
                    accept_header = request.headers.get("accept", "text/html").lower()
                    if "application/json" in accept_header or request.url.path.startswith("/api/"):
                        return JSONResponse(status_code=500, content=error_data)
                    else:
                        error_html = templates_instance.create_fallback_error_html(None, str(e))
                        return HTMLResponse(content=error_html, status_code=500)
                
            return wrapper
        return decorator
    return smart_response

# Usage:
# registry = SmartTemplateRegistry()
# registry.register(User, template_name="user/profile.html", macro_name="render_user")
# templates = SmartFastApiTemplates(directory="templates", registry=registry)
# smart_response = create_smart_response(templates)