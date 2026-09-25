"""
Citation Network Core Modules
=============================
Core API clients for Zotero and OpenAlex, and markdown notes writer for Obsidian.
"""
from src.core.zotero_client import ZoteroClient
from src.core.openalex_client import OpenAlexClient
from src.core.obsidian_writer import ObsidianWriter

__all__ = [
    "ZoteroClient",
    "OpenAlexClient",
    "ObsidianWriter",
]
