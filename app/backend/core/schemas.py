"""Backward-compatible schema exports.

Import schemas from app.backend.schemas going forward.
This file remains as a compatibility layer for existing imports.
"""

from app.backend.schemas import *  # noqa: F401,F403
