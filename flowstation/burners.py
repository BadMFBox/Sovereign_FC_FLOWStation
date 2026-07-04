"""Burner placeholders

This module contains stub interfaces for the "burner" / security helper logic referenced
in FlowStation-v1.1.0-FC_FLOW.py. Replace these stubs with your secure implementations.

Public API (stubs):
- generate_token(room_id, meta) -> dict
- verify_token(token_obj) -> bool
- seal_data(key, data) -> bytes
- unseal_data(key, blob) -> bytes
- store_secure(key, data) -> bool
- retrieve_secure(key) -> bytes | None

All methods currently implement safe no-op or deterministic stubs so you can wire
in real logic later.
"""
from typing import Optional, Dict
import hashlib
import hmac
import base64
import json

# NOTE: Replace these with secure implementations.
_STUB_SECRET = b"flowstation-stub-secret"


def generate_token(room_id: str, meta: Dict) -> Dict:
    """Return a deterministic token-like dict for development.

    TODO: Replace with proper burner token generation.
    """
    payload = {
        "room": room_id,
        "meta": meta,
    }
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    sig = hmac.new(_STUB_SECRET, raw, hashlib.sha256).hexdigest()
    return {"payload": payload, "sig": sig}


def verify_token(token_obj: Dict) -> bool:
    """Verify the stub token. Returns True only if signature matches our stub secret.

    TODO: Implement verification against your secure burner backend.
    """
    try:
        payload = token_obj["payload"]
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        expected = hmac.new(_STUB_SECRET, raw, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, token_obj.get("sig", ""))
    except Exception:
        return False


def seal_data(key: str, data: bytes) -> bytes:
    """Return a base64 "sealed" blob (stub)."""
    return base64.b64encode(data)


def unseal_data(key: str, blob: bytes) -> Optional[bytes]:
    """Return original bytes if possible (stub)."""
    try:
        return base64.b64decode(blob)
    except Exception:
        return None


def store_secure(key: str, data: bytes) -> bool:
    """Store data to a local file (stub). Real burners should use a secure store."""
    try:
        with open(f".secure_{key}", "wb") as f:
            f.write(data)
        return True
    except Exception:
        return False


def retrieve_secure(key: str) -> Optional[bytes]:
    try:
        with open(f".secure_{key}", "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None

