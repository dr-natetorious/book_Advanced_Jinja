"""Database integration for SmartTemplates - SQLModel to/from SQL with SQLite focus."""

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


class SmartDatabaseTemplates(SmartTemplates):
    """
    Database-specific extension of SmartTemplates for SQLModel to/from SQL generation.
    
    Focused on SQLite for simplicity with no external dependencies.
    Generates CREATE TABLE statements and INSERT/SELECT queries from SQLModel classes.
    """

    def __init__(
        self,
        directory: str,
        *,
        registry: SmartTemplateRegistry | None = None,
        debug_mode: bool = False,
        output_dir: str = "db_generated",
        **kwargs: Any,
    ) -> None:
        """
        Initialize SmartDatabaseTemplates.

        Args:
            directory: Template directory path
            registry: Template registry instance
            debug_mode: Enable debug mode for enhanced error reporting
            output_dir: Directory for generated SQL files
            **kwargs: Additional Jinja2 environment options
        """
        super().__init__(directory, registry=registry, debug_mode=debug_mode, **kwargs)
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _prepare_database_context(self, base_context: dict[str, Any]) -> dict[str, Any]:
        """Prepare context with database-specific variables."""
        # CRITICAL: Defensive copy - never mutate input
        template_context = base_context.copy()
        template_context.setdefault("debug_mode", self.debug_mode)
        template_context.setdefault("timestamp", datetime.now())
        template_context.setdefault("output_dir", str(self.output_dir))
        template_context.setdefault("dialect", "sqlite")  # SQLite-first approach
        
        # Add SQLModel version if available
        if SQLMODEL_AVAILABLE:
            import sqlmodel
            template_context.setdefault("sqlmodel_version", sqlmodel.__version__)
        else:
            template_context.setdefault("sqlmodel_version", "not_available")
        
        return template_context

    def _write_output_file(self, content: str, filepath: Path) -> bool:
        """Write generated content to file with error handling."""
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            self._logger.info(f"Generated database file: {filepath}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to write file {filepath}: {e}")
            return False

    def _extract_sqlmodel_table_info(self, model_class: type) -> dict[str, Any]:
        """Extract basic table information from SQLModel class for SQLite."""
        if not SQLMODEL_AVAILABLE:
            return {"error": "SQLModel not available", "class_name": model_class.__name__}
            
        try:
            table_info = {
                "class_name": model_class.__name__,
                "table_name": getattr(model_class, "__tablename__", model_class.__name__.lower()),
                "fields": []
            }
            
            # Extract fields from SQLModel
            if hasattr(model_class, "__fields__"):
                for field_name, field_info in model_class.__fields__.items():
                    # Map Python types to SQLite types (simplified)
                    python_type = str(field_info.annotation)
                    sqlite_type = self._map_python_to_sqlite_type(python_type)
                    
                    field_data = {
                        "name": field_name,
                        "python_type": python_type,
                        "sqlite_type": sqlite_type,
                        "nullable": field_info.default is None or getattr(field_info, "nullable", True),
                        "primary_key": getattr(field_info, "primary_key", False),
                        "foreign_key": getattr(field_info, "foreign_key", None),
                        "unique": getattr(field_info, "unique", False),
                        "default": field_info.default if field_info.default is not None else None
                    }
                    table_info["fields"].append(field_data)
            
            return table_info
            
        except Exception as e:
            self._logger.error(f"Failed to extract SQLModel info from {model_class}: {e}")
            return {"error": str(e), "class_name": model_class.__name__}

    def _map_python_to_sqlite_type(self, python_type: str) -> str:
        """Map Python type annotations to SQLite types."""
        # Handle common type patterns
        python_type = python_type.lower()
        
        if "int" in python_type:
            return "INTEGER"
        elif "float" in python_type:
            return "REAL"
        elif "str" in python_type:
            return "TEXT"
        elif "bool" in python_type:
            return "INTEGER"  # SQLite stores booleans as INTEGER
        elif "date" in python_type:
            return "TEXT"  # SQLite stores dates as TEXT
        elif "datetime" in python_type:
            return "TEXT"  # SQLite stores datetime as TEXT
        else:
            return "TEXT"  # Default fallback

    def generate_create_table_sql(
        self,
        model_classes: list[type],
        *,
        schema_template: str = "create_table_sqlite.sql.j2",
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:
        """
        Generate CREATE TABLE statements from SQLModel classes for SQLite.

        Args:
            model_classes: List of SQLModel classes
            schema_template: Template to use for schema generation
            output_file: Optional output file path

        Returns:
            Tuple of (rendered_content, error_or_none)
        """
        if not SQLMODEL_AVAILABLE:
            error = TemplateErrorDetail(
                error_type="DependencyError",
                message="SQLModel not available. Install with: pip install sqlmodel",
                template_name=schema_template,
                context_data={"sqlmodel_available": False},
            )
            return "", RenderError(error=error)

        try:
            # Extract table information from models
            tables = []
            for model_class in model_classes:
                if issubclass(model_class, SQLModel):
                    table_info = self._extract_sqlmodel_table_info(model_class)
                    if "error" not in table_info:
                        tables.append(table_info)
                    else:
                        self._logger.warning(f"Skipping {model_class}: {table_info['error']}")
                else:
                    self._logger.warning(f"Skipping non-SQLModel class: {model_class}")
            
            base_context = {
                "tables": tables,
                "schema_type": "create_table",
                "table_count": len(tables),
            }

            # CRITICAL: Defensive copy through _prepare_database_context
            template_context = self._prepare_database_context(base_context)

            content, error = self.render_safe(schema_template, template_context)

            if error:
                self._logger.error(
                    f"Failed to render schema template: {error.error.message}"
                )
                return "", error

            if output_file:
                output_path = self.output_dir / output_file
                if self._write_output_file(content, output_path):
                    self._logger.info(f"Schema written to: {output_path}")

            return content, None

        except Exception as e:
            self._logger.exception("Unexpected error in schema generation")
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=schema_template,
                context_data={"model_count": len(model_classes)},
            )
            return "", RenderError(error=error)

    def generate_insert_sql(
        self,
        model_instances: list[Any],
        *,
        insert_template: str = "insert_sqlite.sql.j2",
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:
        """
        Generate INSERT statements from SQLModel instances for SQLite.

        Args:
            model_instances: List of SQLModel instances with data
            insert_template: Template to use for INSERT generation
            output_file: Optional output file path

        Returns:
            Tuple of (rendered_content, error_or_none)
        """
        if not SQLMODEL_AVAILABLE:
            error = TemplateErrorDetail(
                error_type="DependencyError",
                message="SQLModel not available. Install with: pip install sqlmodel",
                template_name=insert_template,
                context_data={"sqlmodel_available": False},
            )
            return "", RenderError(error=error)

        try:
            # Group instances by table
            tables_data = {}
            for instance in model_instances:
                if not isinstance(instance, SQLModel):
                    self._logger.warning(f"Skipping non-SQLModel instance: {type(instance)}")
                    continue
                
                model_class = type(instance)
                table_name = getattr(model_class, "__tablename__", model_class.__name__.lower())
                
                if table_name not in tables_data:
                    tables_data[table_name] = {
                        "table_name": table_name,
                        "class_name": model_class.__name__,
                        "records": []
                    }
                
                # Extract data from instance
                if hasattr(instance, "model_dump"):
                    record_data = instance.model_dump()
                elif hasattr(instance, "dict"):
                    record_data = instance.dict()
                else:
                    record_data = {k: v for k, v in instance.__dict__.items() if not k.startswith('_')}
                
                tables_data[table_name]["records"].append(record_data)
            
            base_context = {
                "tables": list(tables_data.values()),
                "insert_type": "data_insert",
                "total_records": sum(len(table["records"]) for table in tables_data.values()),
            }

            # CRITICAL: Defensive copy through _prepare_database_context
            template_context = self._prepare_database_context(base_context)

            content, error = self.render_safe(insert_template, template_context)

            if error:
                self._logger.error(
                    f"Failed to render insert template: {error.error.message}"
                )
                return "", error

            if output_file:
                output_path = self.output_dir / output_file
                if self._write_output_file(content, output_path):
                    self._logger.info(f"Insert statements written to: {output_path}")

            return content, None

        except Exception as e:
            self._logger.exception("Unexpected error in insert generation")
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=insert_template,
                context_data={"instance_count": len(model_instances)},
            )
            return "", RenderError(error=error)

    def generate_select_sql(
        self,
        model_classes: list[type],
        *,
        select_template: str = "select_sqlite.sql.j2",
        include_joins: bool = True,
        output_file: str | None = None,
    ) -> tuple[str, RenderError | None]:
        """
        Generate SELECT statements for SQLModel classes with basic JOIN support.

        Args:
            model_classes: List of SQLModel classes
            select_template: Template to use for SELECT generation
            include_joins: Whether to include JOIN statements for foreign keys
            output_file: Optional output file path

        Returns:
            Tuple of (rendered_content, error_or_none)
        """
        if not SQLMODEL_AVAILABLE:
            error = TemplateErrorDetail(
                error_type="DependencyError",
                message="SQLModel not available. Install with: pip install sqlmodel",
                template_name=select_template,
                context_data={"sqlmodel_available": False},
            )
            return "", RenderError(error=error)

        try:
            # Extract table information for SELECT generation
            tables = []
            for model_class in model_classes:
                if issubclass(model_class, SQLModel):
                    table_info = self._extract_sqlmodel_table_info(model_class)
                    if "error" not in table_info:
                        # Add JOIN information if requested
                        if include_joins:
                            joins = []
                            for field in table_info["fields"]:
                                if field["foreign_key"]:
                                    # Simple FK parsing (assumes table.column format)
                                    if "." in str(field["foreign_key"]):
                                        fk_table = str(field["foreign_key"]).split(".")[0]
                                        joins.append({
                                            "table": fk_table,
                                            "local_column": field["name"],
                                            "foreign_column": "id"  # Assume 'id' as primary key
                                        })
                            table_info["joins"] = joins
                        
                        tables.append(table_info)
                    else:
                        self._logger.warning(f"Skipping {model_class}: {table_info['error']}")
                else:
                    self._logger.warning(f"Skipping non-SQLModel class: {model_class}")
            
            base_context = {
                "tables": tables,
                "select_type": "basic_select",
                "include_joins": include_joins,
                "table_count": len(tables),
            }

            # CRITICAL: Defensive copy through _prepare_database_context
            template_context = self._prepare_database_context(base_context)

            content, error = self.render_safe(select_template, template_context)

            if error:
                self._logger.error(
                    f"Failed to render select template: {error.error.message}"
                )
                return "", error

            if output_file:
                output_path = self.output_dir / output_file
                if self._write_output_file(content, output_path):
                    self._logger.info(f"Select statements written to: {output_path}")

            return content, None

        except Exception as e:
            self._logger.exception("Unexpected error in select generation")
            error = TemplateErrorDetail(
                error_type=type(e).__name__,
                message=str(e),
                template_name=select_template,
                context_data={"model_count": len(model_classes)},
            )
            return "", RenderError(error=error)


# Usage examples:
# 
# # Generate CREATE TABLE statements for SQLite
# from tests.models.business_objects import School, Course, Student, Enrollment
# 
# db_templates = SmartDatabaseTemplates("db_templates/")
# 
# # Create schema
# schema_sql, error = db_templates.generate_create_table_sql(
#     [School, Course, Student, Enrollment],
#     output_file="schema.sql"
# )
#
# # Generate INSERT statements from instances
# schools, courses, students, enrollments = create_complete_test_data()
# insert_sql, error = db_templates.generate_insert_sql(
#     schools + courses + students + enrollments,
#     output_file="test_data.sql"
# )
#
# # Generate SELECT statements with JOINs
# select_sql, error = db_templates.generate_select_sql(
#     [School, Course, Student, Enrollment],
#     include_joins=True,
#     output_file="queries.sql"
# )