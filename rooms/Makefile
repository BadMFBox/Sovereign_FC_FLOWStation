# ═══════════════════════════════════════════════════════════════
#  4-Room Command Center — UI Build System
#  Sovereign UI for FlowStation
# ═══════════════════════════════════════════════════════════════

.PHONY: help build watch clean test deploy info
.DEFAULT_GOAL := help

# ───────────────────────────────────────────────────────────────
#  COLORS
# ───────────────────────────────────────────────────────────────

CYAN    := \033[96m
GREEN   := \033[92m
YELLOW  := \033[93m
RED     := \033[91m
BOLD    := \033[1m
RESET   := \033[0m
DIM     := \033[2m

# ───────────────────────────────────────────────────────────────
#  PATHS
# ───────────────────────────────────────────────────────────────

ROOMS_DIR    := $(shell pwd)
PROJECT_ROOT := $(shell dirname $(ROOMS_DIR))
BUILD_SCRIPT := $(PROJECT_ROOT)/build_ui.py
FLOWSTATION  := $(PROJECT_ROOT)/FlowStation-v1.1.0-FC_FLOW.py

ROOM1 := room1_command_post.html
ROOM2 := room2_file_status.html
ROOM3 := room3_terminal.html
ROOM4 := room4_ai_chat.html
CLIENT_JS := client.js
LAYOUT := main_layout.html

# ───────────────────────────────────────────────────────────────
#  HELP
# ───────────────────────────────────────────────────────────────

help: ## Show this help
	@echo ""
	@echo "$(CYAN)$(BOLD)╔═══════════════════════════════════════════╗$(RESET)"
	@echo "$(CYAN)$(BOLD)║  4-Room Command Center — UI Build       ║$(RESET)"
	@echo "$(CYAN)$(BOLD)╚═══════════════════════════════════════════╝$(RESET)"
	@echo ""
	@echo "$(BOLD)BUILD$(RESET)"
	@echo "  $(GREEN)make build$(RESET)    Compile rooms into single HTML"
	@echo "  $(GREEN)make watch$(RESET)    Auto-rebuild on file changes"
	@echo ""
	@echo "$(BOLD)DEPLOY$(RESET)"
	@echo "  $(GREEN)make deploy$(RESET)   Build + restart FlowStation"
	@echo "  $(GREEN)make quick$(RESET)    Fast deploy (no full restart)"
	@echo ""
	@echo "$(BOLD)TEST$(RESET)"
	@echo "  $(GREEN)make test$(RESET)     Verify room structure"
	@echo "  $(GREEN)make lint$(RESET)     Check HTML/JS syntax"
	@echo ""
	@echo "$(BOLD)UTILITIES$(RESET)"
	@echo "  $(GREEN)make info$(RESET)     Show room structure"
	@echo "  $(GREEN)make clean$(RESET)    Remove build artifacts"
	@echo ""
	@echo "$(BOLD)EXAMPLES$(RESET)"
	@echo "  $(DIM)# Build and deploy$(RESET)"
	@echo "  $(DIM)make deploy$(RESET)"
	@echo ""
	@echo "  $(DIM)# Watch for changes while developing$(RESET)"
	@echo "  $(DIM)make watch$(RESET)"
	@echo ""

# ───────────────────────────────────────────────────────────────
#  BUILD
# ───────────────────────────────────────────────────────────────

build: ## Compile rooms into single HTML
	@echo ""
	@echo "$(CYAN)$(BOLD)🔨 Building 4-room interface...$(RESET)"
	@if [ ! -f "$(BUILD_SCRIPT)" ]; then \
		echo "$(RED)✗ build_ui.py not found$(RESET)"; \
		exit 1; \
	fi
	@python3 $(BUILD_SCRIPT) > compiled.html
	@echo "  $(GREEN)✓ Built: rooms/compiled.html$(RESET)"
	@echo ""

watch: ## Auto-rebuild on changes
	@echo ""
	@echo "$(CYAN)$(BOLD)👁️  Watching rooms/ for changes...$(RESET)"
	@echo "  $(DIM)Press Ctrl+C to stop$(RESET)"
	@echo ""
	@while true; do \
		inotifywait -q -e modify,create,delete $(ROOM1) $(ROOM2) $(ROOM3) $(ROOM4) $(CLIENT_JS) $(LAYOUT) 2>/dev/null || sleep 2; \
		echo "  $(YELLOW)File changed, rebuilding...$(RESET)"; \
		$(MAKE) build --no-print-directory; \
	done

# ───────────────────────────────────────────────────────────────
#  DEPLOY
# ───────────────────────────────────────────────────────────────

deploy: build ## Build + restart FlowStation
	@echo ""
	@echo "$(CYAN)$(BOLD)🚀 Deploying to FlowStation...$(RESET)"
	@pkill -9 -f FlowStation 2>/dev/null || true
	@sleep 1
	@cd $(PROJECT_ROOT) && python3 -u $(FLOWSTATION) 2>&1 | tee flowstation.log &
	@sleep 2
	@echo "  $(GREEN)✓ FlowStation restarted$(RESET)"
	@echo ""
	@echo "  $(DIM)Open: http://localhost:8080$(RESET)"
	@echo ""

quick: build ## Fast deploy (SIGHUP instead of restart)
	@echo ""
	@echo "$(CYAN)$(BOLD)⚡ Quick deploy...$(RESET)"
	@pkill -HUP -f FlowStation 2>/dev/null || echo "  $(YELLOW)FlowStation not running$(RESET)"
	@echo "  $(GREEN)✓ Sent reload signal$(RESET)"
	@echo ""

# ───────────────────────────────────────────────────────────────
#  TEST
# ───────────────────────────────────────────────────────────────

test: ## Verify room structure
	@echo ""
	@echo "$(CYAN)$(BOLD)🧪 Testing room modules...$(RESET)"
	@for room in $(ROOM1) $(ROOM2) $(ROOM3) $(ROOM4); do \
		echo "  Testing $$room..."; \
		grep -q "room-header" $$room && echo "    $(GREEN)✓ Has header$(RESET)" || echo "    $(RED)✗ Missing header$(RESET)"; \
		grep -q "room-content" $$room && echo "    $(GREEN)✓ Has content$(RESET)" || echo "    $(RED)✗ Missing content$(RESET)"; \
	done
	@echo "  Testing $(CLIENT_JS)..."
	@grep -q "connectWebSocket" $(CLIENT_JS) && echo "    $(GREEN)✓ Has WebSocket logic$(RESET)" || echo "    $(RED)✗ Missing WebSocket$(RESET)"
	@grep -q "handleWebSocketMessage" $(CLIENT_JS) && echo "    $(GREEN)✓ Has message handler$(RESET)" || echo "    $(RED)✗ Missing handler$(RESET)"
	@echo ""

lint: ## Check HTML/JS syntax (requires tidy & eslint)
	@echo ""
	@echo "$(CYAN)$(BOLD)🔍 Linting...$(RESET)"
	@command -v tidy >/dev/null 2>&1 && \
		(tidy -q -e $(ROOM1) $(ROOM2) $(ROOM3) $(ROOM4) 2>&1 | grep -v "Warning" || true) || \
		echo "  $(DIM)tidy not installed, skipping HTML validation$(RESET)"
	@command -v eslint >/dev/null 2>&1 && \
		eslint $(CLIENT_JS) || \
		echo "  $(DIM)eslint not installed, skipping JS validation$(RESET)"
	@echo ""

# ───────────────────────────────────────────────────────────────
#  UTILITIES
# ───────────────────────────────────────────────────────────────

info: ## Show room structure
	@echo ""
	@echo "$(CYAN)$(BOLD)📁 4-Room Command Center Structure$(RESET)"
	@echo ""
	@echo "  rooms/"
	@echo "  ├── $(ROOM1)  $(DIM)(cyan)   — Engine control, pipeline$(RESET)"
	@echo "  ├── $(ROOM2)   $(DIM)(green)  — Room states, file tracking$(RESET)"
	@echo "  ├── $(ROOM3)      $(DIM)(gold)   — Live execution, commands$(RESET)"
	@echo "  ├── $(ROOM4)       $(DIM)(pink)   — AI interaction$(RESET)"
	@echo "  ├── $(CLIENT_JS)                $(DIM)— WebSocket & logic$(RESET)"
	@echo "  ├── $(LAYOUT)                 $(DIM)— Grid structure$(RESET)"
	@echo "  └── Makefile                          $(DIM)— This file$(RESET)"
	@echo ""
	@echo "$(BOLD)Commands:$(RESET)"
	@echo "  make build   — Compile rooms into single HTML"
	@echo "  make watch   — Auto-rebuild on changes"
	@echo "  make deploy  — Build + restart FlowStation"
	@echo "  make test    — Verify room structure"
	@echo "  make clean   — Remove build artifacts"
	@echo ""

clean: ## Remove build artifacts
	@echo ""
	@echo "$(YELLOW)$(BOLD)🧹 Cleaning...$(RESET)"
	@rm -f compiled.html
	@echo "  $(GREEN)✓ Cleaned$(RESET)"
	@echo ""

# ───────────────────────────────────────────────────────────────
#  GUARDS
# ───────────────────────────────────────────────────────────────

.PHONY: check-build-script
check-build-script:
	@if [ ! -f "$(BUILD_SCRIPT)" ]; then \
		echo "$(RED)✗ build_ui.py not found at $(BUILD_SCRIPT)$(RESET)"; \
		exit 1; \
	fi
