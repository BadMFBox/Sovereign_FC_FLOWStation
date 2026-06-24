#!/usr/bin/env python3
"""
Project structure organization guide for Sovereign-FlowStation.
Run this to see the recommended file organization.
"""

print("""
📁 SOVEREIGN FLOWSTATION — ORGANIZED STRUCTURE
═══════════════════════════════════════════════════════════════

src/
├── python/
│   ├── core/              # Core pipeline logic
│   │   ├── flow_lock.py       (Phase 1: Logic locking)
│   │   ├── flow_split.py      (Phase 2: Module splitting)
│   │   ├── flow_sort.py       (Phase 3: File sorting)
│   │   └── flow_integrate.py  (Phase 4: Integration & sealing)
│   ├── tools/             # Utility tools
│   │   ├── lab_status.py      (Status reporting)
│   │   └── agentsroom_2_agent.py
│   └── notes/             # Documentation
│       └── FlowStationLab_Notes.py
│
├── typescript/
│   ├── extension/         # Extension entry point
│   │   └── extension.ts
│   ├── managers/          # Session & status management
│   │   ├── SessionManager.ts
│   │   └── StatusBarManager.ts
│   ├── views/             # Tree views & panels
│   │   ├── AuditTreeView.ts
│   │   ├── MeshTreeView.ts
│   │   ├── RoomTreeView.ts
│   │   └── FluidScanner.ts
│   ├── panels/            # UI Panels
│   │   ├── DialogPanel.ts
│   │   ├── SessionPanel.ts
│   │   ├── FluidDialog.ts
│   │   ├── Room1Panel.ts
│   │   └── Room2Panel.ts
│   ├── bridge/            # Python-TS bridge
│   │   ├── BridgeConnector.ts
│   │   ├── TerminalBridge.ts
│   │   └── TerminalBridgeFactory.ts
│   ├── communication/     # Message bus
│   │   └── MessageBus.ts
│   └── registry/          # Command registry
│       └── CommandRegistry.ts
│
└── cpp/                   # C++ mesh core
    ├── include/
    │   └── aizquad_mesh_core.hpp
    ├── src/
    │   └── mesh<room>bindings.cpp
    └── tests/
        └── test_mesh_core.cpp

tests/
├── python/
│   ├── test_lock.py
│   ├── test_split.py
│   ├── test_sort.py
│   ├── test_integrate.py
│   ├── test_end_to_end.py
│   ├── conftest.py
│   └── test_runner.sh
│
└── typescript/
    └── bridge.test.ts

build/
├── CMakeLists.txt
├── CMakeLists (1).txt  ← Remove or merge
└── Makefile

config/
├── devcontainer/
│   ├── devcontainer.json
│   └── post-create.sh
├── tsconfig.json
├── package.json         ← Main extension manifest
├── pyproject.toml
└── requirements.txt

.github/
└── workflows/
    └── fs-scan.yml

docs/
├── README.md
└── ARCHITECTURE.md

examples/
└── bridge_usage.ts

root/
├── .gitignore
├── LICENSE
└── package-lock.json (if needed)

═══════════════════════════════════════════════════════════════
DUPLICATES TO REMOVE:
- FlowStationLab_Notes.py (keep 1, delete (1) and (2))
- BridgeConnector (1).ts (merge with BridgeConnector.ts)
- CMakeLists (1).txt (merge with CMakeLists.txt)
- README (1).md (merge with README.md)
- package.json (1) and (2) (keep main, merge configs)
- tsconfig (1).json (keep main)
- FLOWSTATION files (keep main, remove (1))
- The Core Tool — flow_lock files (keep .py, remove duplicates)

═══════════════════════════════════════════════════════════════
""")
