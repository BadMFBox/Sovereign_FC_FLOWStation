// ═══════════════════════════════════════════════════════════════
//  SessionManager.ts
//  PIN-gated session state for VS Code extension
// ═══════════════════════════════════════════════════════════════

import * as vscode       from "vscode";
import * as crypto       from "crypto";
import { BridgeConnector } from "./BridgeConnector";
import { EventEmitter }  from "events";

export type SessionState = "locked" | "unlocked" | "expired";

export interface SessionInfo {
  state:       SessionState;
  unlockedAt:  string | null;
  expiresAt:   string | null;
  timeRemaining: number;      // seconds
  user:        string;
}

export class SessionManager extends EventEmitter {

  private state:      SessionState = "locked";
  private unlockedAt: Date | null  = null;
  private timeoutMs:  number;

  constructor(
    private context: vscode.ExtensionContext,
    private bridge:  BridgeConnector
  ) {
    super();

    const config = vscode.workspace.getConfiguration("flowstation");
    this.timeoutMs = (config.get<number>("sessionTimeout") ?? 30) * 60 * 1000;

    // Restore session state if within timeout
    this.restoreSession();
  }

  // ── Public API ──────────────────────────────────────────────

  async unlock(): Promise<boolean> {
    const pin = await vscode.window.showInputBox({
      prompt:      "Enter FlowStation PIN",
      password:    true,
      placeHolder: "••••••",
      validateInput: v => v.length < 4
        ? "PIN must be at least 4 characters"
        : null
    });

    if (!pin) return false;

    // Verify PIN via bridge
    const ok = await this.bridge.verifyPin(pin);
    if (!ok) {
      vscode.window.showErrorMessage("❌ FlowStation: Wrong PIN");
      this.bridge.audit("SESSION_UNLOCK_FAILED", "session", "wrong PIN");
      return false;
    }

    // Set session state
    this.state      = "unlocked";
    this.unlockedAt = new Date();

    // Persist for restore
    this.context.workspaceState.update("flowstation.sessionState", {
      unlockedAt: this.unlockedAt.toISOString(),
    });

    this.bridge.audit("SESSION_UNLOCKED", "session", `timeout=${this.timeoutMs}ms`);
    this.emit("unlocked");
    return true;
  }

  lock(): void {
    this.state      = "locked";
    this.unlockedAt = null;
    this.context.workspaceState.update("flowstation.sessionState", null);
    this.bridge.audit("SESSION_LOCKED", "session", "manual lock");
    this.emit("locked");
  }

  expire(): void {
    this.state      = "expired";
    this.unlockedAt = null;
    this.context.workspaceState.update("flowstation.sessionState", null);
    this.bridge.audit("SESSION_EXPIRED", "session", "timeout");
    this.emit("expired");
  }

  isUnlocked():  boolean { return this.state === "unlocked" && !this.isExpired(); }
  isLocked():    boolean { return this.state === "locked"; }

  isExpired(): boolean {
    if (this.state !== "unlocked" || !this.unlockedAt) return false;
    return Date.now() - this.unlockedAt.getTime() > this.timeoutMs;
  }

  getInfo(): SessionInfo {
    const remaining = this.unlockedAt
      ? Math.max(
          0,
          this.timeoutMs - (Date.now() - this.unlockedAt.getTime())
        ) / 1000
      : 0;

    return {
      state:         this.state,
      unlockedAt:    this.unlockedAt?.toISOString() ?? null,
      expiresAt:     this.unlockedAt
        ? new Date(this.unlockedAt.getTime() + this.timeoutMs).toISOString()
        : null,
      timeRemaining: Math.round(remaining),
      user:          "owner",
    };
  }

  // ── Private ─────────────────────────────────────────────────

  private restoreSession(): void {
    const saved = this.context.workspaceState.get<{ unlockedAt: string }>(
      "flowstation.sessionState"
    );

    if (!saved) return;

    const unlockedAt = new Date(saved.unlockedAt);
    const elapsed    = Date.now() - unlockedAt.getTime();

    if (elapsed < this.timeoutMs) {
      this.state      = "unlocked";
      this.unlockedAt = unlockedAt;
      this.emit("unlocked");
    }
  }

  destroy(): void {
    this.removeAllListeners();
  }
}
