"""
Route modules for SmartTemplates API tests.

This package contains modular route implementations that demonstrate
different aspects of SmartTemplates FastAPI integration:

- schools.py: CRUD operations with dashboard templates
- students.py: Status-based template selection
- courses.py: Role-based view variations (instructor/student)

Each module provides setup functions that configure routes with
appropriate template registrations and smart_response decorators.
"""

from .schools import setup_school_routes
from .students import setup_student_routes

__all__ = [
    "setup_school_routes", 
    "setup_student_routes"
]