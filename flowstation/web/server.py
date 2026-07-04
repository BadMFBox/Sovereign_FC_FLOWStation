"""HTTP server placeholder

Place HTTP server implementation here. Implement static file serving and
routing to handlers in flowstation.web.handlers.
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler


def start_http_server(host: str, port: int):
    print(f"[flowstation.web.server] start {host}:{port} (placeholder)")
    # TODO: replace with real server and handlers
