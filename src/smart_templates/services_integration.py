"""Service integration for SmartTemplates - Full-stack CRUD generation from data models."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .core import RenderError, SmartTemplateRegistry, SmartTemplates, TemplateErrorDetail

try:
    from sqlmodel import SQLModel
    SQLMODEL_AVAILABLE = True
except ImportError:
    SQLMODEL_AVAILABLE = False

# Import our specialized templates
from .fastapi_integration import SmartFastApiTemplates
from .pytest_integration import SmartPytestTemplates
from .database_integration import SmartDatabaseTemplates


class ServiceGenerationConfig(BaseModel):
    """Configuration for full-stack service generation."""
    
    # Project structure
    project_name: str
    output_dir: str = "generated_service"
    
    # Component toggles
    generate_fastapi: bool = True
    generate_tests: bool = True
    generate_database: bool = True
    generate_frontend: bool = False  # Future enhancement
    
    # FastAPI configuration
    api_prefix: str = "/api/v1"
    enable_auth: bool = False
    cors_enabled: bool = True
    
    # Database configuration
    database_url: str = "sqlite:///./app.db"
    include_test_data: bool = True
    
    # Testing configuration
    test_framework: str = "pytest"
    include_integration_tests: bool = True
    include_performance_tests: bool = False


class SmartServiceTemplates(SmartTemplates):
    """
    Service-level template orchestrator that combines FastAPI, PyTest, and Database
    templates to generate complete CRUD applications from data models.
    """

    def __init__(
        self,
        directory: str,
        *,
        registry: SmartTemplateRegistry | None = None,
        debug_mode: bool = False,
        output_dir: str = "generated_services",
        **kwargs: Any,
    ) -> None:
        """
        Initialize SmartServiceTemplates.

        Args:
            directory: Template directory path
            registry: Template registry instance
            debug_mode: Enable debug mode for enhanced error reporting
            output_dir: Directory for generated service projects
            **kwargs: Additional Jinja2 environment options
        """
        super().__init__(directory, registry=registry, debug_mode=debug_mode, **kwargs)
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize specialized template engines
        self._setup_specialized_templates()

    def _setup_specialized_templates(self) -> None:
        """Initialize the specialized template engines with shared registry."""
        try:
            # Use shared registry for consistency
            self.fastapi_templates = SmartFastApiTemplates(
                str(self.env.loader.searchpath[0]),  # Use same template directory
                registry=self.registry,
                debug_mode=self.debug_mode
            )
            
            self.pytest_templates = SmartPytestTemplates(
                str(self.env.loader.searchpath[0]),
                registry=self.registry,
                debug_mode=self.debug_mode
            )
            
            self.database_templates = SmartDatabaseTemplates(
                str(self.env.loader.searchpath[0]),
                registry=self.registry,
                debug_mode=self.debug_mode
            )
            
            self._logger.info("Specialized template engines initialized successfully")
            
        except Exception as e:
            self._logger.error(f"Failed to initialize specialized templates: {e}")
            # Create minimal fallbacks to prevent crashes
            self.fastapi_templates = None
            self.pytest_templates = None
            self.database_templates = None

    def _prepare_service_context(self, base_context: dict[str, Any]) -> dict[str, Any]:
        """Prepare context with service-specific variables."""
        # CRITICAL: Defensive copy - never mutate input
        template_context = base_context.copy()
        template_context.setdefault("debug_mode", self.debug_mode)
        template_context.setdefault("timestamp", datetime.now())
        template_context.setdefault("output_dir", str(self.output_dir))
        template_context.setdefault("generator", "SmartServiceTemplates")
        
        # Add component availability
        template_context.setdefault("fastapi_available", self.fastapi_templates is not None)
        template_context.setdefault("pytest_available", self.pytest_templates is not None)
        template_context.setdefault("database_available", self.database_templates is not None)
        template_context.setdefault("sqlmodel_available", SQLMODEL_AVAILABLE)
        
        return template_context

    def _write_output_file(self, content: str, filepath: Path) -> bool:
        """Write generated content to file with error handling."""
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            self._logger.info(f"Generated service file: {filepath}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to write file {filepath}: {e}")
            return False

    def _extract_model_metadata(self, model_classes: list[type]) -> list[dict[str, Any]]:
        """Extract metadata from model classes for service generation."""
        models_metadata = []
        
        for model_class in model_classes:
            model_info = {
                "class_name": model_class.__name__,
                "table_name": getattr(model_class, "__tablename__", model_class.__name__.lower()),
                "module_name": model_class.__module__,
                "is_sqlmodel": SQLMODEL_AVAILABLE and issubclass(model_class, SQLModel),
                "is_basemodel": issubclass(model_class, BaseModel),
                "fields": [],
                "relationships": [],
                "crud_operations": ["create", "read", "update", "delete"]
            }
            
            # Extract fields
            if hasattr(model_class, "__fields__"):
                for field_name, field_info in model_class.__fields__.items():
                    field_data = {
                        "name": field_name,
                        "type": str(field_info.annotation),
                        "nullable": field_info.default is None,
                        "primary_key": getattr(field_info, "primary_key", False),
                        "foreign_key": getattr(field_info, "foreign_key", None),
                        "unique": getattr(field_info, "unique", False),
                        "searchable": field_name in ["name", "title", "email"],  # Common searchable fields
                        "filterable": getattr(field_info, "index", False) or field_name in ["status", "type", "category"]
                    }
                    model_info["fields"].append(field_data)
            
            # Identify primary key field
            primary_key_fields = [f for f in model_info["fields"] if f["primary_key"]]
            model_info["primary_key"] = primary_key_fields[0]["name"] if primary_key_fields else "id"
            
            models_metadata.append(model_info)
        
        return models_metadata

    def generate_full_service(
        self,
        model_classes: list[type],
        config: ServiceGenerationConfig,
        *,
        service_template: str = "full_service.py.j2",
    ) -> tuple[dict[str, str], RenderError | None]:
        """
        Generate complete CRUD service from model classes.

        Args:
            model_classes: List of SQLModel classes to generate service for
            config: Service generation configuration
            service_template: Template to use for service generation

        Returns:
            Tuple of (generated_files_dict, error_or_none)
        """
        if not SQLMODEL_AVAILABLE:
            error = TemplateErrorDetail(
                error_type="DependencyError",
                message="SQLModel not available. Install with: pip install sqlmodel",
                template_name=service_template,
                context_data={"sqlmodel_available": False},
            )
            return {}, RenderError(error=error)

        try:
            # Extract model metadata
            models_metadata = self._extract_model_metadata(model_classes)
            
            # Prepare project structure
            project_dir = self.output_dir / config.project_name
            generated_files = {}
            
            # Base context for all generation
            base_context = {
                "config": config.model_dump(),
                "models": models_metadata,
                "project_name": config.project_name,
                "model_count": len(model_classes),
            }
            
            # CRITICAL: Defensive copy through _prepare_service_context
            service_context = self._prepare_service_context(base_context)
            
            # Generate database schema
            if config.generate_database and self.database_templates:
                schema_content, db_error = self.database_templates.generate_create_table_sql(
                    model_classes,
                    output_file=None  # We'll handle file writing
                )
                if db_error:
                    self._logger.error(f"Database generation failed: {db_error.error.message}")
                    return {}, db_error
                
                schema_file = project_dir / "database" / "schema.sql"
                if self._write_output_file(schema_content, schema_file):
                    generated_files["database/schema.sql"] = schema_content
                
                # Generate test data if requested
                if config.include_test_data:
                    # Create sample instances for test data
                    sample_instances = self._create_sample_instances(model_classes)
                    if sample_instances:
                        insert_content, insert_error = self.database_templates.generate_insert_sql(
                            sample_instances,
                            output_file=None
                        )
                        if not insert_error:
                            test_data_file = project_dir / "database" / "test_data.sql"
                            if self._write_output_file(insert_content, test_data_file):
                                generated_files["database/test_data.sql"] = insert_content
            
            # Generate FastAPI application
            if config.generate_fastapi and self.fastapi_templates:
                fastapi_content, fastapi_error = self._generate_fastapi_app(
                    models_metadata, service_context, project_dir
                )
                if fastapi_error:
                    self._logger.error(f"FastAPI generation failed: {fastapi_error.error.message}")
                    return generated_files, fastapi_error
                
                generated_files.update(fastapi_content)
            
            # Generate tests
            if config.generate_tests and self.pytest_templates:
                test_content, test_error = self._generate_tests(
                    models_metadata, service_context, project_dir
                )
                if test_error:
                    self._logger.error(f"Test generation failed: {test_error.error.message}")
                    return generated_files, test_error
                
                generated_files.update(test_content)
            
            # Generate project configuration files
            config_content, config_error = self._generate_project_config(
                service_context, project_dir
            )
            if config_error:
                self._logger.error(f"Config generation failed: {config_error.error.message}")
                return generated_files, config_error
            
            generated_files.update(config_content)
            
            self._logger.info(f"Generated complete service with {len(generated_files)} files")
            return generated_files, None

        except Exception as e:
            self._logger.exception("Unexpected error in service generation")
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=service_template,
                context_data={"model_count": len(model_classes)},
            )
            return {}, RenderError(error=error)

    def _create_sample_instances(self, model_classes: list[type]) -> list[Any]:
        """Create sample instances for test data generation."""
        # This is a simplified version - could be enhanced with factory functions
        sample_instances = []
        
        for model_class in model_classes:
            try:
                # Create minimal instance with required fields
                if hasattr(model_class, "__fields__"):
                    field_values = {}
                    for field_name, field_info in model_class.__fields__.items():
                        if field_info.default is None and not getattr(field_info, "nullable", True):
                            # Required field - provide sample value
                            field_type = str(field_info.annotation).lower()
                            if "int" in field_type:
                                field_values[field_name] = 1
                            elif "str" in field_type:
                                field_values[field_name] = f"Sample {field_name}"
                            elif "bool" in field_type:
                                field_values[field_name] = True
                    
                    if field_values:  # Only create if we have required fields
                        instance = model_class(**field_values)
                        sample_instances.append(instance)
                        
            except Exception as e:
                self._logger.warning(f"Could not create sample instance for {model_class}: {e}")
        
        return sample_instances

    def _generate_fastapi_app(
        self, 
        models_metadata: list[dict], 
        context: dict[str, Any], 
        project_dir: Path
    ) -> tuple[dict[str, str], RenderError | None]:
        """Generate FastAPI application files."""
        generated_files = {}
        
        try:
            # Main FastAPI app
            app_context = context.copy()
            app_context["models"] = models_metadata
            
            app_content, error = self.render_safe("fastapi/main.py.j2", app_context)
            if error:
                return {}, error
            
            app_file = project_dir / "app" / "main.py"
            if self._write_output_file(app_content, app_file):
                generated_files["app/main.py"] = app_content
            
            # Generate CRUD routes for each model
            for model in models_metadata:
                route_context = context.copy()
                route_context["model"] = model
                
                route_content, route_error = self.render_safe("fastapi/crud_routes.py.j2", route_context)
                if not route_error:
                    route_file = project_dir / "app" / "routes" / f"{model['table_name']}.py"
                    if self._write_output_file(route_content, route_file):
                        generated_files[f"app/routes/{model['table_name']}.py"] = route_content
            
            # Database connection
            db_context = context.copy()
            db_content, db_error = self.render_safe("fastapi/database.py.j2", db_context)
            if not db_error:
                db_file = project_dir / "app" / "database.py"
                if self._write_output_file(db_content, db_file):
                    generated_files["app/database.py"] = db_content
            
            return generated_files, None
            
        except Exception as e:
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=f"FastAPI generation error: {e}",
                context_data={"model_count": len(models_metadata)},
            )
            return generated_files, RenderError(error=error)

    def _generate_tests(
        self, 
        models_metadata: list[dict], 
        context: dict[str, Any], 
        project_dir: Path
    ) -> tuple[dict[str, str], RenderError | None]:
        """Generate test files."""
        generated_files = {}
        
        try:
            # Test configuration
            test_context = context.copy()
            test_context["models"] = models_metadata
            
            conftest_content, error = self.render_safe("tests/conftest.py.j2", test_context)
            if error:
                return {}, error
            
            conftest_file = project_dir / "tests" / "conftest.py"
            if self._write_output_file(conftest_content, conftest_file):
                generated_files["tests/conftest.py"] = conftest_content
            
            # Generate tests for each model
            for model in models_metadata:
                model_test_context = context.copy()
                model_test_context["model"] = model
                
                test_content, test_error = self.render_safe("tests/test_crud.py.j2", model_test_context)
                if not test_error:
                    test_file = project_dir / "tests" / f"test_{model['table_name']}.py"
                    if self._write_output_file(test_content, test_file):
                        generated_files[f"tests/test_{model['table_name']}.py"] = test_content
            
            return generated_files, None
            
        except Exception as e:
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=f"Test generation error: {e}",
                context_data={"model_count": len(models_metadata)},
            )
            return generated_files, RenderError(error=error)

    def _generate_project_config(
        self, 
        context: dict[str, Any], 
        project_dir: Path
    ) -> tuple[dict[str, str], RenderError | None]:
        """Generate project configuration files."""
        generated_files = {}
        
        try:
            config_files = [
                ("pyproject.toml.j2", "pyproject.toml"),
                ("requirements.txt.j2", "requirements.txt"),
                ("README.md.j2", "README.md"),
                ("docker/Dockerfile.j2", "Dockerfile"),
                (".env.template.j2", ".env.template"),
            ]
            
            for template_name, output_name in config_files:
                content, error = self.render_safe(template_name, context)
                if not error:
                    output_file = project_dir / output_name
                    if self._write_output_file(content, output_file):
                        generated_files[output_name] = content
                else:
                    self._logger.warning(f"Could not generate {output_name}: {error.error.message}")
            
            return generated_files, None
            
        except Exception as e:
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=f"Config generation error: {e}",
                context_data={"context_keys": list(context.keys())},
            )
            return generated_files, RenderError(error=error)

    def generate_api_documentation(
        self,
        model_classes: list[type],
        *,
        docs_template: str = "api_docs.md.j2",
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:
        """
        Generate API documentation from model classes.

        Args:
            model_classes: List of model classes
            docs_template: Template to use for documentation generation
            output_file: Optional output file path

        Returns:
            Tuple of (rendered_content, error_or_none)
        """
        try:
            models_metadata = self._extract_model_metadata(model_classes)
            
            base_context = {
                "models": models_metadata,
                "doc_type": "api_documentation",
                "model_count": len(models_metadata),
            }

            # CRITICAL: Defensive copy through _prepare_service_context
            template_context = self._prepare_service_context(base_context)

            content, error = self.render_safe(docs_template, template_context)

            if error:
                self._logger.error(
                    f"Failed to render documentation template: {error.error.message}"
                )
                return "", error

            if output_file:
                output_path = self.output_dir / output_file
                if self._write_output_file(content, output_path):
                    self._logger.info(f"API documentation written to: {output_path}")

            return content, None

        except Exception as e:
            self._logger.exception("Unexpected error in documentation generation")
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=docs_template,
                context_data={"model_count": len(model_classes)},
            )
            return "", RenderError(error=error)


# Usage examples:
#
# # Generate complete CRUD service
# from tests.models.business_objects import School, Course, Student, Enrollment
# 
# service_templates = SmartServiceTemplates("service_templates/")
# 
# config = ServiceGenerationConfig(
#     project_name="education_api",
#     generate_fastapi=True,
#     generate_tests=True,
#     generate_database=True,
#     api_prefix="/api/v1",
#     database_url="sqlite:///./education.db"
# )
# 
# generated_files, error = service_templates.generate_full_service(
#     [School, Course, Student, Enrollment],
#     config
# )
# 
# if not error:
#     print(f"Generated {len(generated_files)} files:")
#     for filepath in generated_files.keys():
#         print(f"  - {filepath}")
# else:
#     print(f"Generation failed: {error.error.message}")