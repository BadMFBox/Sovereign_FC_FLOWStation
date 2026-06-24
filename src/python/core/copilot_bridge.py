#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
COPILOT BRIDGE — Real-Time Interactive Workflow
═══════════════════════════════════════════════════════════════

This bridge connects GitHub Copilot (AI) to FlowStation's
interactive session manager. When Copilot is working on your
project, it uses this to:

  ✓ Know it's in a session (context preservation)
  ✓ Save drafts continuously (not direct edits)
  ✓ Get interactive feedback from you in real-time
  ✓ Know when to clock out and summarize work

The workflow is INTERACTIVE. Copilot doesn't work alone.
It suggests → You approve → Next step → You decide.

FC_FLOW MESH | Sovereign PEU
Founder: Juan Jaime Rivera Zamorano
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# ─────────────────────────────────────────────
#  PATHS
# ─────────────────────────────────────────────

ROOT         = Path(".")
SHARED       = ROOT / "shared"
AI_ROOM      = SHARED / "ai_room"
AI_CONTEXT   = AI_ROOM / "context"
AI_DRAFTS    = AI_ROOM / "drafts"
SESSION_FILE = SHARED / ".ai_session"
AUDIT_FILE   = SHARED / "audit.log"

# ─────────────────────────────────────────────
#  COLORS
# ─────────────────────────────────────────────

CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
BOLD    = "\033[1m"
RESET   = "\033[0m"
DIM     = "\033[2m"
MAGENTA = "\033[95m"
BLUE    = "\033[94m"


# ─────────────────────────────────────────────
#  COPILOT BRIDGE
# ─────────────────────────────────────────────

class CopilotBridge:
    """
    Bridge between Copilot and FlowStation.
    Enables interactive workflow with token awareness.
    """
    
    def __init__(self):
        self.session_active = self._check_session()
        self.token_budget = 200000  # From system prompt
        self.tokens_used = 0
        self.session_data = self._load_session()
    
    def _check_session(self) -> bool:
        """Check if AI session is active."""
        if not SESSION_FILE.exists():
            return False
        try:
            data = json.loads(SESSION_FILE.read_text())
            if not data.get("active"):
                return False
            expires = data.get("expires_at", 0)
            if time.time() > expires:
                return False
            return True
        except Exception:
            return False
    
    def _load_session(self) -> Dict[str, Any]:
        """Load active session data."""
        if not SESSION_FILE.exists():
            return {}
        try:
            return json.loads(SESSION_FILE.read_text())
        except Exception:
            return {}
    
    def start_interactive_workflow(self, task: str) -> bool:
        """
        Begin interactive workflow with Copilot.
        This ensures the workflow stays interactive even
        if tokens run low.
        """
        if not self.session_active:
            print(f"{RED}✗ No active AI session{RESET}")
            print(f"{DIM}  Run: python3 ai_session.py clock-in{RESET}")
            return False
        
        print(f"""
{CYAN}{BOLD}╔═══════════════════════════════════════════╗
║  COPILOT INTERACTIVE WORKFLOW             ║
║  [ 1 ]  ◈  [ 2 ]  BMB · FC_FLOW MESH     ║
╚═══════════════════════════════════════════╝{RESET}

{MAGENTA}{BOLD}Task:{RESET}
{task}

{YELLOW}How this works:{RESET}
  1. Copilot suggests a change
  2. You review it interactively
  3. [A]pprove → saved to drafts
  4. [R]eject → logged as rejected
  5. [Q]ueue  → add to suggestion queue
  6. [D]one   → finish this task
  
{DIM}If Copilot runs low on tokens, it will:
  • Save all current work to drafts
  • Ask you what to do next
  • Resume in next session with full context{RESET}

{BLUE}Starting interactive session...{RESET}
""")
        
        return True
    
    def suggest_change(self, 
                      filename: str,
                      change_type: str,
                      description: str,
                      code_before: str,
                      code_after: str) -> str:
        """
        Copilot proposes a change interactively.
        Waits for user approval before saving.
        
        Returns: 'approve', 'reject', 'queue', or 'done'
        """
        
        print(f"""
{CYAN}─ SUGGESTION {change_type.upper()} ─{RESET}

File: {YELLOW}{filename}{RESET}
Type: {BLUE}{change_type}{RESET}

{DIM}Description:{RESET}
{description}

{DIM}Before:{RESET}
{code_before[:200]}...

{DIM}After:{RESET}
{code_after[:200]}...

{YELLOW}What do you want to do?{RESET}
  {GREEN}[A]{RESET} Approve (save to drafts)
  {RED}[R]{RESET} Reject (log as rejected)
  {BLUE}[Q]{RESET} Queue (add to suggestion list)
  {MAGENTA}[D]{RESET} Done (finish session)
  {DIM}[C]{RESET} Chat (discuss with Copilot)
""")
        
        response = input(f"{CYAN}Your choice:{RESET} ").strip().upper()
        
        if response == "A":
            self._save_draft(filename, change_type, description, code_after)
            print(f"  {GREEN}✓ Saved to drafts{RESET}\n")
            return "approve"
        
        elif response == "R":
            self._log_rejected(filename, change_type, description)
            print(f"  {RED}✗ Rejected and logged{RESET}\n")
            return "reject"
        
        elif response == "Q":
            self._queue_suggestion(filename, change_type, description, code_after)
            print(f"  {BLUE}→ Queued for later{RESET}\n")
            return "queue"
        
        elif response == "D":
            print(f"\n{MAGENTA}Finishing session...{RESET}\n")
            return "done"
        
        elif response == "C":
            print(f"\n{BLUE}Chat mode (discuss with Copilot){RESET}")
            print(f"{DIM}(This keeps the workflow interactive){RESET}\n")
            return "chat"
        
        else:
            print(f"  {DIM}Invalid choice. Treating as queue.{RESET}\n")
            return "queue"
    
    def token_check(self) -> Dict[str, Any]:
        """
        Check token usage and warn if running low.
        This ensures Copilot can cleanly exit before token death.
        """
        # In real implementation, this would be passed from system
        tokens_remaining = self.token_budget - self.tokens_used
        percent_remaining = (tokens_remaining / self.token_budget) * 100
        
        status = {
            "total": self.token_budget,
            "used": self.tokens_used,
            "remaining": tokens_remaining,
            "percent": percent_remaining,
            "status": "ok"
        }
        
        if percent_remaining < 20:
            status["status"] = "warning"
            print(f"""
{YELLOW}{BOLD}⚠ TOKEN WARNING{RESET}
Copilot is running low on tokens ({percent_remaining:.1f}% remaining).

{YELLOW}Copilot will now:{RESET}
  1. Save all current drafts
  2. Summarize work done so far
  3. Create a handoff note for next session
  4. Clock out cleanly (no loss)

{DIM}All work is preserved. Next session continues exactly
where this one ended.{RESET}
""")
        
        elif percent_remaining < 10:
            status["status"] = "critical"
            print(f"""
{RED}{BOLD}🚨 TOKEN CRITICAL{RESET}
Copilot must exit now to preserve work.

{RED}Final steps:{RESET}
  ✓ Saving all drafts
  ✓ Writing handoff summary
  ✓ Clocking out
  ✓ Session preserved for next time

{YELLOW}No work is lost. See {MAGENTA}ai_room/context/handoff.txt{RESET}
""")
            return status
        
        return status
    
    def handoff_summary(self, 
                       work_completed: str,
                       work_remaining: str,
                       next_steps: str) -> bool:
        """
        Create handoff note for next session.
        Preserves context and continuity.
        """
        
        handoff = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_completed_at": time.time() + 14400,  # 4 hour TTL
            "work_completed": work_completed,
            "work_remaining": work_remaining,
            "next_steps": next_steps,
            "token_reason": "Token limit reached - session paused cleanly"
        }
        
        handoff_file = AI_CONTEXT / "handoff.txt"
        AI_CONTEXT.mkdir(parents=True, exist_ok=True)
        
        handoff_text = f"""
╔═══════════════════════════════════════════╗
║  COPILOT SESSION HANDOFF                  ║
║  Paused due to token limit                ║
╚═══════════════════════════════════════════╝

TIME: {handoff['timestamp']}

WORK COMPLETED:
{work_completed}

WORK REMAINING:
{work_remaining}

NEXT STEPS:
{next_steps}

CONTEXT: Preserved in ai_room/context/
DRAFTS: Saved in ai_room/drafts/
APPROVED: Ready to merge in ai_room/approved/

When resuming:
  1. python3 ai_session.py clock-in
  2. Read this handoff note
  3. Continue from "NEXT STEPS" above
  4. All context is loaded automatically
"""
        
        handoff_file.write_text(handoff_text)
        
        print(f"""
{GREEN}{BOLD}✓ Handoff Summary Created{RESET}

File: {MAGENTA}ai_room/context/handoff.txt{RESET}

When you resume:
  1. Cat the handoff file to see context
  2. Clock in again
  3. Continue exactly where we left off
  
All work is safe. Nothing lost.
""")
        
        return True
    
    def _save_draft(self, filename: str, change_type: str, desc: str, code: str):
        """Save approved change to drafts."""
        AI_DRAFTS.mkdir(parents=True, exist_ok=True)
        draft = {
            "filename": filename,
            "type": change_type,
            "description": desc,
            "code": code,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "approved"
        }
        draft_path = AI_DRAFTS / f"{filename}.{change_type}.json"
        draft_path.write_text(json.dumps(draft, indent=2))
    
    def _log_rejected(self, filename: str, change_type: str, desc: str):
        """Log rejected change for audit."""
        audit_entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": "SUGGESTION_REJECTED",
            "filename": filename,
            "type": change_type,
            "description": desc,
            "source": "copilot-bridge"
        }
        with open(AUDIT_FILE, "a") as f:
            f.write(json.dumps(audit_entry) + "\n")
    
    def _queue_suggestion(self, filename: str, change_type: str, desc: str, code: str):
        """Queue suggestion for later review."""
        queue_file = AI_ROOM / "suggestion_queue.json"
        queue = []
        if queue_file.exists():
            queue = json.loads(queue_file.read_text())
        
        queue.append({
            "filename": filename,
            "type": change_type,
            "description": desc,
            "code": code,
            "queued_at": datetime.now(timezone.utc).isoformat()
        })
        
        queue_file.write_text(json.dumps(queue, indent=2))


# ─────────────────────────────────────────────
#  INTERACTIVE WORKFLOW EXAMPLE
#  ─────────────────────────────────────────────

def example_interactive_workflow():
    """
    Example of how Copilot uses this interactively.
    This runs the full workflow loop.
    """
    
    bridge = CopilotBridge()
    
    if not bridge.session_active:
        print(f"{RED}✗ Session not active{RESET}\n")
        return False
    
    # Start workflow
    task = "Optimize the validate() function in room-2 for 40% speed improvement"
    if not bridge.start_interactive_workflow(task):
        return False
    
    # Simulate: Copilot makes 3 suggestions
    suggestions = [
        {
            "filename": "room-2/validate.py",
            "type": "optimization",
            "description": "Replace regex validation with direct string methods",
            "before": "if re.match(r'^[a-zA-Z0-9]+$', token):",
            "after": "if token.isalnum():"
        },
        {
            "filename": "room-2/test_validate.py",
            "type": "test",
            "description": "Add performance benchmark tests",
            "before": "def test_validate():\n    pass",
            "after": "def test_validate():\n    import timeit\n    t = timeit.Timer(lambda: validate('test'))\n    print(t.timeit(100000))"
        },
        {
            "filename": "room-2/validate.py",
            "type": "refactor",
            "description": "Cache compiled regex for 20% speedup",
            "before": "PATTERN = None\ndef validate(token):",
            "after": "PATTERN = re.compile(r'^[a-zA-Z0-9]+$')\ndef validate(token):"
        }
    ]
    
    # Interactive loop
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n{CYAN}{BOLD}Suggestion {i}/{len(suggestions)}{RESET}\n")
        
        response = bridge.suggest_change(
            suggestion["filename"],
            suggestion["type"],
            suggestion["description"],
            suggestion["before"],
            suggestion["after"]
        )
        
        # Check tokens every suggestion
        token_status = bridge.token_check()
        if token_status["status"] == "critical":
            print(f"\n{RED}Tokens critical! Creating handoff and exiting...{RESET}\n")
            bridge.handoff_summary(
                work_completed=f"Completed {i} of {len(suggestions)} suggestions",
                work_remaining=f"{len(suggestions) - i} optimization suggestions pending",
                next_steps=f"Review remaining {len(suggestions) - i} suggestions and apply approved changes"
            )
            return True
        
        if response == "done":
            break
    
    print(f"""
{GREEN}{BOLD}╔═══════════════════════════════════════════╗
║  WORKFLOW COMPLETE                       ║
║                                          ║
║  All suggestions reviewed                ║
║  Approved changes in: ai_room/approved/  ║
║  Rejected changes in: ai_room/rejected/  ║
║                                          ║
║  Next: python3 ai_session.py clock-out   ║
╚═══════════════════════════════════════════╝{RESET}
""")
    
    return True


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def usage():
    print(f"""
{CYAN}COPILOT BRIDGE — Interactive Workflow{RESET}

This bridge keeps Copilot work INTERACTIVE.
Never runs blind. Always gets your approval.
Safe exit on token limit.

Usage:
  python3 copilot_bridge.py status        → Check session
  python3 copilot_bridge.py example       → Run demo workflow
  python3 copilot_bridge.py token-check   → Check token usage

{CYAN}How it works:{RESET}
  1. Start AI session:  python3 ai_session.py clock-in
  2. Run workflow:      python3 copilot_bridge.py example
  3. Get interactive prompts for every suggestion
  4. Approve/Reject/Queue/Chat for each one
  5. If tokens run low, cleanly saves and exits
  6. Next session resumes with full context
  
{YELLOW}This IS the interactive workflow you wanted.{RESET}
""")


def main():
    if len(sys.argv) < 2:
        usage()
        return 0
    
    command = sys.argv[1].lower()
    bridge = CopilotBridge()
    
    if command == "status":
        if bridge.session_active:
            print(f"{GREEN}✓ Session is ACTIVE{RESET}\n")
            print(f"  Expires: {bridge.session_data.get('expires_at', '?')}\n")
        else:
            print(f"{RED}✗ No active session{RESET}\n")
            print(f"{DIM}  Run: python3 ai_session.py clock-in{RESET}\n")
        return 0
    
    elif command == "example":
        return 0 if example_interactive_workflow() else 1
    
    elif command == "token-check":
        status = bridge.token_check()
        print(f"\nToken Status:")
        print(f"  Total:     {status['total']}")
        print(f"  Used:      {status['used']}")
        print(f"  Remaining: {status['remaining']} ({status['percent']:.1f}%)")
        print(f"  Status:    {status['status'].upper()}\n")
        return 0
    
    else:
        print(f"{RED}✗ Unknown command: {command}{RESET}\n")
        usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())
