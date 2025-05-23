from importlib.metadata import version

__version__ = version("gmaps-scraper")   # reads pyproject.toml metadata

from .gmaps import get_google_map_details
