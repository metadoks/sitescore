"""SiteScore FAZ 5 versioned machine-consumer API."""

from .app import app, create_app
from .version import API_VERSION, __version__

__all__ = ["API_VERSION", "__version__", "app", "create_app"]
