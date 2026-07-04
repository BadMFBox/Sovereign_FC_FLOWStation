"""HTTP request handlers (placeholder)

Implement route handlers used by the UI and API: index, assets, /api/ endpoints.
"""


def handle_index(request):
    return """<html><body><h1>FlowStation UI (placeholder)</h1></body></html>"""


def handle_api_command(request, payload):
    # TODO: dispatch commands to flowstation.api/commands
    return {"ok": True, "received": payload}
