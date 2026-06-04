// ═══════════════════════════════════════════════════════════════
//  StatusBarManager.ts
//  Live status bar — session state + room counts
// ═══════════════════════════════════════════════════════════════

import * as vscode       from "vscode";
import { SessionManager } from "./SessionManager";

export class StatusBarManager {

  private sessionItem: vscode.StatusBarItem;
  private roomItem:    vscode.StatusBarItem;

  constructor(
    private context: vscode.ExtensionContext,
    private session: SessionManager
  ) {
    // Session status — left side
    this.sessionItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left, 100
    );
    this.sessionItem.show();

    // Room count — left side
    this.roomItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left, 99
    );
    this.roomItem.show();

    // Listen to session events
    session.on("unlocked", () => this.update());
    session.on("locked",   () => this.update());
    session.on("expired",  () => this.update());

    context.subscriptions.push(this.sessionItem);
    context.subscriptions.push(this.roomItem);

    // Initial render
    this.update();
  }

  update(): void {
    const info = this.session.getInfo();

    // ── Session item ─────────────────────────────────────────
    if (info.state === "unlocked") {
      const minutes = Math.floor(info.timeRemaining / 60);
      const seconds = info.timeRemaining % 60;
      const timeStr = minutes > 0
        ? `${minutes}m`
        : `${seconds}s`;

      this.sessionItem.text            = `$(unlock) FlowStation ${timeStr}`;
      this.sessionItem.tooltip         = `Session active — expires in ${timeStr}\nClick to lock`;
      this.sessionItem.command         = "flowstation.lock";
      this.sessionItem.backgroundColor = undefined;
      this.sessionItem.color           = new vscode.ThemeColor(
        "statusBarItem.warningForeground"
      );

    } else if (info.state === "expired") {
      this.sessionItem.text            = `$(clock) FlowStation Expired`;
      this.sessionItem.tooltip         = "Session expired — click to unlock";
      this.sessionItem.command         = "flowstation.unlock";
      this.sessionItem.backgroundColor = new vscode.ThemeColor(
        "statusBarItem.errorBackground"
      );

    } else {
      this.sessionItem.text            = `$(lock) FlowStation`;
      this.sessionItem.tooltip         = "FlowStation locked — click to unlock";
      this.sessionItem.command         = "flowstation.unlock";
      this.sessionItem.backgroundColor = undefined;
      this.sessionItem.color           = undefined;
    }
  }

  updateRoomCount(locked: number, total: number): void {
    this.roomItem.text    = `$(database) ${locked}/${total} locked`;
    this.roomItem.tooltip = `${locked} of ${total} rooms locked\nClick to view rooms`;
    this.roomItem.command = "flowstation.refreshRooms";
  }

  destroy(): void {
    this.sessionItem.dispose();
    this.roomItem.dispose();
  }
}
