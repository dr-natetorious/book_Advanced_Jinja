"""
SmartTemplates - Framework-agnostic template engine with object-based resolution.

A modern template engine that provides:
- Object-based template resolution with fallback hierarchy
- Framework-agnostic core with specialized FastAPI and pytest integrations
- Structured error handling with debugging capabilities
- Macro support for reusable template components
- Convention-based naming with custom pattern support

Basic Usage:
    >>> from smart_templates import SmartTemplates, SmartTemplateRegistry
    >>> registry = SmartTemplateRegistry()
    >>> templates = SmartTemplates("templates/", registry=registry)
    >>> content, error = templates.render_safe("user/profile.html", {"user": user})

FastAPI Integration:
    >>> from smart_templates.fastapi_integration import SmartFastApiTemplates
    >>> templates = SmartFastApiTemplates("templates/")
    >>> # Use with @smart_response decorator for automatic content negotiation

Pytest Integration:
    >>> from smart_templates.pytest_integration import SmartPytestTemplates
    >>> templates = SmartPytestTemplates("templates/")
    >>> # Generate test reports and fixtures from templates
"""

__version__ = "0.1.0"
__author__ = "Nate Bachmeier"
__license__ = "MIT"

# Core exports - always available
from .core import (
    RenderError,
    SmartTemplateRegistry,
    SmartTemplates,
    TemplateErrorDetail,
)

# Public API
__all__ = [
    # Core classes
    "SmartTemplates",
    "SmartTemplateRegistry",
    # Error handling
    "RenderError",
    "TemplateErrorDetail",
    # Package metadata
    "__version__",
]


# Optional integrations - imported on demand to avoid hard dependencies
def __getattr__(name: str) -> object:
    """
    Lazy import for optional integrations.

    This allows importing optional components without requiring their dependencies
    to be installed unless actually used.

    Example:
        >>> from smart_templates import SmartFastApiTemplates  # Only requires FastAPI if used
        >>> from smart_templates import SmartPytestTemplates   # Only requires pytest if used
    """
    if name == "SmartFastApiTemplates":
        try:
            from .fastapi_integration import SmartFastApiTemplates

            return SmartFastApiTemplates
        except ImportError as e:
            raise ImportError(
                "SmartFastApiTemplates requires FastAPI. Install with: "
                "pip install smart-templates[fastapi]"
            ) from e

    elif name == "create_smart_response":
        try:
            from .fastapi_integration import create_smart_response

            return create_smart_response
        except ImportError as e:
            raise ImportError(
                "create_smart_response requires FastAPI. Install with: "
                "pip install smart-templates[fastapi]"
            ) from e

    elif name == "SmartPytestTemplates":
        try:
            from .pytest_integration import SmartPytestTemplates

            return SmartPytestTemplates
        except ImportError as e:
            raise ImportError(
                "SmartPytestTemplates requires pytest. Install with: "
                "pip install smart-templates[testing]"
            ) from e

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# For IDEs and static analysis - these will be available when dependencies are installed
if False:  # TYPE_CHECKING equivalent without typing import
    from .fastapi_integration import SmartFastApiTemplates, create_smart_response
    from .pytest_integration import SmartPytestTemplates

    __all__.extend(
        [
            "SmartFastApiTemplates",
            "create_smart_response",
            "SmartPytestTemplates",
        ]
    )
