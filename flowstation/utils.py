"""Utility helpers (stubs)

Small helpers used across modules. Add implementations as needed.
"""
import json
import hashlib


def to_json(obj) -> str:
    return json.dumps(obj, default=str, sort_keys=True)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

