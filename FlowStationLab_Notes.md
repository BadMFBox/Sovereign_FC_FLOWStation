# FlowStation Lab - File System Map

This file lists the proposed detailed repository file tree for FlowStation. Many
entries below are intentionally empty placeholder files so you can drop in your
real logic, assets, and tests. Use this as the single source-of-truth map for
organizing the project.

Notes:
- I did NOT change any existing burner implementations. The burner module
  (flowstation/burners.py) remains as-is; do not edit it here unless you want
  to replace the stub with production code.
- Place production assets (images, braid/volume files) under flowstation/assets/
  and remove or replace the placeholder files.
- Each section contains a short description and the exact file path to create.

Top-level (project root)
- FlowStation-v1.1.0-FC_FLOW.py  # original monolith (keep running as-is)
- FlowStationLab_Notes.md        # this file (mapping & guide)
- DEVNOTES.md                    # developer notes already added in branch

Python package (flowstation/)
- flowstation/__init__.py        # existing shim (exports cli)
- flowstation/cli.py             # entrypoint shim
- flowstation/config.py          # constants & config loader
- flowstation/core.py            # core classes: FlowState, LoopValidator, HealthScorer
- flowstation/utils.py           # helpers
- flowstation/burners.py         # DO NOT modify for now (your secure burners live here)
- flowstation/assets.py          # asset resolver (placeholders ok)
- flowstation/web_ws_stub.py     # simple web/ws stubs (existing)

Web server (HTTP) module
- flowstation/web/__init__.py
- flowstation/web/server.py        # HTTPServer wrapper, static file serving
- flowstation/web/handlers.py      # Request handlers for API + UI routes
- flowstation/web/templates/       # optional Jinja/ejs templates
  - flowstation/web/templates/index.html
- flowstation/web/static/          # static assets served by HTTP
  - flowstation/web/static/css/    # CSS files
  - flowstation/web/static/js/     # JS bundles
  - flowstation/web/static/img/    # images

WebSocket module
- flowstation/ws/__init__.py
- flowstation/ws/manager.py        # client registry, broadcast helpers
- flowstation/ws/protocols.py      # message types / framing helpers

API module
- flowstation/api.py               # REST endpoints used by the UI
- flowstation/api/commands.py      # command handlers invoked by API

Storage & assets
- flowstation/storage/__init__.py
- flowstation/storage/secure_store.py  # secure key/value store (stubbed)
- flowstation/storage/volume_manager.py # volume mount / braid handling
- flowstation/assets/placeholders/     # placeholder assets for missing files
  - flowstation/assets/placeholders/volume_one_braid.png
  - flowstation/assets/placeholders/missing_image.png

Modules (business logic)
- flowstation/modules/__init__.py
- flowstation/modules/volume.py        # higher-level volume/asset helpers
- flowstation/modules/rooms.py         # room lifecycle & defaults
- flowstation/modules/validators.py    # loop & validation helpers

Scripts & tooling
- scripts/start_flowstation.sh    # small helper to create venv & run server
- scripts/build_extension.sh      # placeholder for VS Code extension build steps

Documentation
- docs/architecture.md
- docs/deployment.md
- docs/rooms.md

Tests
- flowstation/tests/test_imports.py  # already present
- tests/test_web.py                  # http tests (placeholder)
- tests/test_ws.py                   # websocket tests (placeholder)

How to use this map
1. Add your real burner / security code into flowstation/burners.py when ready.
2. Drop volume/ braid files under flowstation/assets/ and update assets.get_asset_path.
3. Implement web.server and ws.manager (or wire the monolith handlers into these modules).
4. Use the scripts/ helpers to run the service locally during dev.

If you want, I can create the skeleton files listed above now (empty with
headers) so you can start filling them. I will NOT touch flowstation/burners.py
per your request. Reply "Create skeleton" to have these files created in the
refactor/modularize-burners branch.
