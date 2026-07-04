"""WebSocket manager (placeholder)

Keep client registry and simple broadcast helpers here.
"""
from typing import Dict

clients: Dict[str, object] = {}


def register_client(client_id: str, ws):
    clients[client_id] = ws


def broadcast(message: str):
    for c in list(clients.values()):
        try:
            c.send(message)
        except Exception:
            pass
