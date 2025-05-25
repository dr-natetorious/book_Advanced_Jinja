# SmartTemplates Pytest Integration - Best Practices Guidance

## **Critical Patterns to Apply from core.py and fastapi_integration.py**

### **✅ MANDATORY Modern Python Patterns:**

#### **1. Import & Type Hint Modernization**
```python
from __future__ import annotations

# Modern type hints (Python 3.10+)
from typing import Any, Callable  # Only what's needed, no Union
# Use: str | None instead of Optional[str]
# Use: dict[str, Any] instead of Dict[str, Any]  
# Use: list[str] instead of List[str]
```

#### **2. Constructor Pattern**
```python
def __init__(
    self,
    directory: str,
    *,  # Force keyword-only arguments
    registry: SmartTemplateRegistry | None = None,
    debug_mode: bool = False,
    output_dir: str = "test_reports",  # pytest-specific config
    **kwargs: Any,
) -> None:
    super().__init__(directory, registry=registry, debug_mode=debug_mode, **kwargs)
    self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    self.output_dir = output_dir
```

#### **3. Context Copying Pattern (CRITICAL)**
```python
def generate_test_report(self, test_data: dict[str, Any], template_name: str) -> tuple[str, RenderError | None]:
    # ALWAYS copy context, never mutate input
    template_context = test_data.copy()
    template_context.setdefault("debug_mode", self.debug_mode)
    template_context.setdefault("timestamp", datetime.now())
    
    return self.render_safe(template_name, template_context)
```

#### **4. Method Signatures with Keyword-Only Args**
```python
def generate_fixtures(
    self, 
    objects: list[Any], 
    *,  # Force keyword-only for optional params
    fixture_template: str = "pytest_fixture.py.j2",
    output_file: str | None = None,
) -> tuple[str, RenderError | None]:
```

#### **5. Instance-Based Logging**
```python
# In __init__:
self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

# In methods:
self._logger.warning(f"Failed to generate test case: {e}")
# NOT: logger.warning() or logging.warning()
```

### **✅ Pytest-Specific Features to Implement:**

#### **1. Test Report Generation**
```python
def generate_test_report(
    self,
    test_results: dict[str, Any],
    *,
    template_name: str = "test_report.html",
    format_type: str = "html",
) -> tuple[str, RenderError | None]:
    """Generate test execution reports from pytest results."""
```

#### **2. Fixture Generation from Objects**
```python
def generate_pytest_fixtures(
    self,
    model_objects: list[Any],
    *,
    fixture_template: str = "fixtures.py.j2", 
    output_file: str | None = None,
) -> tuple[str, RenderError | None]:
    """Generate pytest fixtures from business objects."""
```

#### **3. Test Case Template Generation**
```python
def generate_test_cases(
    self,
    objects: list[Any],
    *,
    test_template: str = "test_cases.py.j2",
    parametrize: bool = True,
) -> tuple[str, RenderError | None]:
    """Generate parametrized test cases from objects."""
```

#### **4. Documentation Generation**
```python
def generate_test_documentation(
    self,
    test_data: dict[str, Any],
    *,
    doc_template: str = "test_docs.md",
    format_type: str = "markdown",
) -> tuple[str, RenderError | None]:
    """Generate test documentation from templates."""
```

### **❌ CRITICAL: What NOT to Include**

#### **1. NO Global Variables**
```python
# ❌ DON'T DO THIS:
logger = logging.getLogger(__name__)
DEFAULT_CONFIG = {...}

# ✅ DO THIS:
class SmartPytestTemplates:
    def __init__(self, ...):
        self._logger = logging.getLogger(...)
        self._config = {...}
```

#### **2. NO Input Parameter Mutation**
```python
# ❌ DON'T DO THIS:
def generate_report(self, context: dict[str, Any]) -> str:
    context["timestamp"] = datetime.now()  # Mutating input!
    
# ✅ DO THIS:
def generate_report(self, context: dict[str, Any]) -> tuple[str, RenderError | None]:
    template_context = context.copy()  # Defensive copy
    template_context.setdefault("timestamp", datetime.now())
```

#### **3. NO Positional Arguments for Optional Params**
```python
# ❌ DON'T DO THIS:
def generate_fixtures(self, objects, template_name, output_file=None):

# ✅ DO THIS:
def generate_fixtures(self, objects: list[Any], *, template_name: str, output_file: str | None = None):
```

### **🎯 Pytest Integration Specific Patterns:**

#### **1. Error Handling for Test Generation**
```python
try:
    # Generate test content
    content, error = self.render_safe(template_name, template_context)
    if error:
        self._logger.error(f"Failed to render test template: {error.error.message}")
        return "", error
    return content, None
except Exception as e:
    self._logger.exception("Unexpected error in test generation")
    # Return structured error using same pattern as core.py
```

#### **2. File Output with Error Handling**
```python
def _write_output_file(self, content: str, filepath: str) -> bool:
    """Write generated content to file with error handling."""
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        Path(filepath).write_text(content, encoding="utf-8")
        self._logger.info(f"Generated test file: {filepath}")
        return True
    except Exception as e:
        self._logger.error(f"Failed to write file {filepath}: {e}")
        return False
```

#### **3. Template Context Preparation**
```python
def _prepare_test_context(self, base_context: dict[str, Any]) -> dict[str, Any]:
    """Prepare context with pytest-specific variables."""
    template_context = base_context.copy()  # Defensive copy
    template_context.setdefault("debug_mode", self.debug_mode)
    template_context.setdefault("timestamp", datetime.now())
    template_context.setdefault("pytest_version", pytest.__version__ if 'pytest' in globals() else "unknown")
    return template_context
```

### **📋 Complete Method Signature Examples:**

```python
class SmartPytestTemplates(SmartTemplates):
    def __init__(
        self,
        directory: str,
        *,
        registry: SmartTemplateRegistry | None = None,
        debug_mode: bool = False,
        output_dir: str = "test_reports",
        **kwargs: Any,
    ) -> None:

    def generate_test_report(
        self,
        test_results: dict[str, Any],
        *,
        template_name: str = "test_report.html",
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:

    def generate_pytest_fixtures(
        self,
        model_objects: list[Any],
        *,
        fixture_template: str = "fixtures.py.j2",
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:

    def generate_test_cases(
        self,
        objects: list[Any],
        *,
        test_template: str = "test_cases.py.j2",
        parametrize: bool = True,
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:

    def generate_test_documentation(
        self,
        test_data: dict[str, Any],
        *,
        doc_template: str = "test_docs.md",
        format_type: str = "markdown",
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:
```

### **🚀 Key Success Criteria:**

1. **Consistency**: Same patterns as core.py and fastapi_integration.py
2. **Modern Python**: 3.10+ type hints, no Union imports
3. **Defensive Programming**: Never mutate inputs, always copy contexts
4. **Instance-Based**: No global variables, everything explicit
5. **Error Handling**: Structured RenderError responses
6. **Logging**: Instance-based logger with qualified names
7. **API Design**: Keyword-only optional parameters

This ensures the pytest integration maintains the same high quality and consistency as the existing modules while providing powerful test automation capabilities.