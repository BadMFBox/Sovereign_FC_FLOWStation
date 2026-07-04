"""Assets / volume placeholders

This module provides helper functions to resolve assets referenced by the web UI or
FlowStation logic (images, volume data, braid/volume assets). If an asset is missing
we return a small placeholder and log a warning.

TODO: Replace placeholder assets with your committed files.
"""
import os
from typing import Optional

ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
PLACEHOLDER = os.path.join(ASSET_DIR, "placeholders")


def get_asset_path(name: str) -> Optional[str]:
    """Return filesystem path for asset name or None if not found."""
    # try direct path in repo assets
    candidate = os.path.join(ASSET_DIR, name)
    if os.path.exists(candidate):
        return candidate
    # try placeholders
    candidate = os.path.join(PLACEHOLDER, name)
    if os.path.exists(candidate):
        return candidate
    # common extensions
    for ext in (".png", ".jpg", ".svg", ".json"):
        candidate = os.path.join(ASSET_DIR, f"{name}{ext}")
        if os.path.exists(candidate):
            return candidate
        candidate = os.path.join(PLACEHOLDER, f"{name}{ext}")
        if os.path.exists(candidate):
            return candidate
    return None


def list_assets() -> list:
    """Return a list of file names in the asset dir (placeholder-aware)."""
    results = []
    if os.path.isdir(ASSET_DIR):
        for root, dirs, files in os.walk(ASSET_DIR):
            for f in files:
                results.append(os.path.relpath(os.path.join(root, f), ASSET_DIR))
    return results

