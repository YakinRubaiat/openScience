"""REST API for openScience (FastAPI).

Exposes the application factory and settings for convenience::

    from openscience.api import create_app
    app = create_app()
"""

from openscience.api.config import APISettings, get_settings
from openscience.api.main import app, create_app

__all__ = ["APISettings", "app", "create_app", "get_settings"]
