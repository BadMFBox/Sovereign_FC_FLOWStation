"""Shim: small wrapper for the original FlowStation-v1.1.0-FC_FLOW.py

This file does not change the original monolith. It exists to show where you
can call into modularized components from the original script.

We do not overwrite the main script; this shim is here for reference/import.
"""
from .cli import start_server, run_from_args

__all__ = ["start_server", "run_from_args"]
