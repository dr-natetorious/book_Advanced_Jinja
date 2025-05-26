"""
API integration tests for SmartTemplates FastAPI integration.

This package contains end-to-end tests that verify the complete FastAPI
integration including routes, templates, and business scenarios.

Test Structure:
- app.py: Test FastAPI application with real routes
- routes/: Route modules organized by business domain
- test_integration.py: End-to-end integration tests

The API tests validate:
- Content negotiation (JSON vs HTML responses)
- Template rendering with business objects  
- Error handling and fallback templates
- Route-level template registration
- Business scenario workflows

Usage:
    # Run all API tests
    pytest tests/api/

    # Run specific integration tests
    pytest tests/api/test_integration.py

    # Test with actual FastAPI test client
    pytest tests/api/ -v
"""

from .app import app, templates

__all__ = [
    "app",
    "templates",
]