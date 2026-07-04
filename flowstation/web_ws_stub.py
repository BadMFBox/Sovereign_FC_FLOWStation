"""Minimal web/ws placeholders

These modules are intentionally minimal: they provide signatures and explanatory
TODOs so you can implement the actual webserver and websocket logic.

They do NOT start any server; use flowstation.cli.start_server to wire up the
web and ws implementations.
"""

# web.py
from typing import Optional


def start_http_server(host: str, port: int):
    """Start the HTTP server that serves the UI.

    TODO: implement request handlers and static file serving.
    """
    print(f"[flowstation.web] start_http_server {host}:{port} (stub)")


# ws.py

def start_ws_server(host: str, port: int):
    """Start the WebSocket server.

    TODO: implement websocket accept, client registry, broadcast.
    """
    print(f"[flowstation.ws] start_ws_server {host}:{port} (stub)")
