"""DEVNOTES: mapping & TODO

This file maps the major logical areas in FlowStation-v1.1.0-FC_FLOW.py to
modules created in this branch (refactor/modularize-burners). It also lists
missing items (stubs) that you should implement.

Purpose: give you a simple checklist and files to drop your real logic into.
"""

Mapping (monolith -> module)
- Configuration constants (top-level constants) -> flowstation.config
- Burner / token / secure-store helpers -> flowstation.burners
- Asset / volume / braid files -> flowstation.assets
- Core state classes (GearState, LoopValidator, HealthScorer, FlowState) -> flowstation.core
- CLI entrypoint / process start -> flowstation.cli
- Small helpers -> flowstation.utils

Stubs created for you (place implementations here):
- flowstation/burners.py
  - generate_token(room_id, meta) -> dict
  - verify_token(token_obj) -> bool
  - seal_data / unseal_data
  - store_secure / retrieve_secure

- flowstation/assets.py
  - get_asset_path(name) -> path|None
  - list_assets()
  - Placeholder images: flowstation/assets/placeholders/* (create files here)

- flowstation/core.py
  - GearState, BuzzkillTier, LoopStatus, LoopValidator, HealthScorer, FlowState

- flowstation/cli.py
  - start_server() and run_from_args() used by shim

How to proceed:
1) Replace functions in flowstation/burners.py with your production burners.
2) Drop your volume/braid files under flowstation/assets or update get_asset_path.
3) Move logic from FlowStation-v1.1.0-FC_FLOW.py into core/web/ws modules as you prefer.

Notes:
- I kept the stubs conservative and non-breaking; the original monolith file is
  unchanged on this branch so you can still run it directly until you migrate.
- When you add implementations, run pytest in the repo root to ensure imports
  remain valid: `python -m pytest -q`.

