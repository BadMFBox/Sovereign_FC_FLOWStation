// ═══════════════════════════════════════════════════════════════
//  CommandRegistry.ts
//  All VS Code commands for FlowStation
// ═══════════════════════════════════════════════════════════════

import * as vscode        from "vscode";
import { BridgeConnector } from "./BridgeConnector";
import { SessionManager }  from "./SessionManager";
import { RoomTreeView }    from "./RoomTreeView";
import { MeshTreeView }    from "./MeshTreeView";
import { AuditTreeView }   from "./AuditTreeView";
import { DialogPanel }     from "./DialogPanel";

export class CommandRegistry {

  private output: vscode.OutputChannel;

  constructor(
    private context:    vscode.ExtensionContext,
    private bridge:     BridgeConnector,
    private session:    SessionManager,
    private roomTree:   RoomTreeView,
    private meshTree:   MeshTreeView,
    private auditTree:  AuditTreeView
  ) {
    this.output = vscode.window.createOutputChannel(
      "FlowStation"
    );
    context.subscriptions.push(this.output);
  }

  registerAll(): void {
    this.register("flowstation.unlock",       () => this.cmdUnlock());
    this.register("flowstation.lock",         () => this.cmdLock());
    this.register("flowstation.openDialog",   () => this.cmdOpenDialog());
    this.register("flowstation.refreshRooms", () => this.cmdRefresh());
    this.register("flowstation.viewAudit",    () => this.cmdViewAudit());
    this.register("flowstation.lockRoom",     (item) => this.cmdRoomAction("lock",      item));
    this.register("flowstation.splitRoom",    (item) => this.cmdRoomAction("split",     item));
    this.register("flowstation.sortRoom",     (item) => this.cmdRoomAction("sort",      item));
    this.register("flowstation.integrateRoom",(item) => this.cmdRoomAction("integrate", item));
    this.register("flowstation.verifyRoom",   (item) => this.cmdRoomAction("verify",    item));
  }

  // ── Command implementations ──────────────────────────────────

  private async cmdUnlock(): Promise<void> {
    const ok = await this.session.unlock();
    if (ok) {
      this.roomTree.refresh();
      vscode.window.showInformationMessage(
        "⚡ FlowStation unlocked"
      );
    }
  }

  private cmdLock(): void {
    this.session.lock();
    this.roomTree.refresh();
    vscode.window.showInformationMessage(
      "🔒 FlowStation locked"
    );
  }

  private async cmdOpenDialog(): Promise<void> {
    if (!this.session.isUnlocked()) {
      const unlock = await vscode.window.showWarningMessage(
        "FlowStation is locked.",
        "Unlock"
      );
      if (unlock !== "Unlock") return;
      const ok = await this.session.unlock();
      if (!ok) return;
    }

    // Pick a room
    const rooms = this.bridge.listActiveRooms();
    if (rooms.length === 0) {
      vscode.window.showErrorMessage(
        "No rooms found in forge/active/"
      );
      return;
    }

    const room = await vscode.window.showQuickPick(rooms, {
      placeHolder: "Select a room to work on",
      title:       "FlowStation — Open Dialog",
    });
    if (!room) return;

    const version = await vscode.window.showInputBox({
      prompt:      "Enter version tag",
      value:       "v1",
      placeHolder: "e.g. v1, v2.1",
    });
    if (!version) return;

    // Check for saved state
    const hasSaved = this.bridge.isRoomLocked(room);
    let resume = false;

    if (hasSaved) {
      const choice = await vscode.window.showQuickPick(
        ["Start fresh", "Resume saved dialog"],
        { title: "Saved dialog state found" }
      );
      resume = choice === "Resume saved dialog";
    }

    DialogPanel.open(
      this.context,
      this.bridge,
      this.session,
      room,
      version,
      resume
    );
  }

  private cmdRefresh(): void {
    this.roomTree.refresh();
    this.meshTree.refresh();
    this.auditTree.refresh();
  }

  private cmdViewAudit(): void {
    const entries = this.bridge.getRecentAudit(50);
    this.output.clear();
    this.output.appendLine("═══════════════════════════════════════");
    this.output.appendLine("  FlowStation Audit Log (last 50)");
    this.output.appendLine("═══════════════════════════════════════");
    for (const entry of entries) {
      this.output.appendLine(entry);
    }
    this.output.show();
  }

  private async cmdRoomAction(
    action: string,
    item:   unknown
  ): Promise<void> {
    if (!this.session.isUnlocked()) {
      vscode.window.showErrorMessage(
        "FlowStation is locked. Unlock first."
      );
      return;
    }

    // Get room from tree item or quick pick
    let room: string | undefined;
    if (item && (item as { roomName?: string }).roomName) {
      room = (item as { roomName: string }).roomName;
    } else {
      const rooms = this.bridge.listActiveRooms();
      room = await vscode.window.showQuickPick(rooms, {
        placeHolder: `Select room to ${action}`,
      });
    }

    if (!room) return;

    const version = await vscode.window.showInputBox({
      prompt: `Version for ${action}`,
      value:  "v1",
    });
    if (!version) return;

    // Confirm before running
    const confirm = await vscode.window.showWarningMessage(
      `Run ${action.toUpperCase()} on ${room} @ ${version}?`,
      { modal: true },
      "Run"
    );
    if (confirm !== "Run") return;

    // Run with live output
    this.output.clear();
    this.output.appendLine(`🔄 Running ${action} on ${room} @ ${version}...`);
    this.output.show();

    const ok = await vscode.window.withProgress(
      {
        location:  vscode.ProgressLocation.Notification,
        title:     `FlowStation: ${action} ${room}`,
        cancellable: false,
      },
      async () => this.bridge.runAction(action, room!, version, this.output)
    );

    if (ok) {
      vscode.window.showInformationMessage(
        `✅ ${action} complete for ${room}`
      );
      this.bridge.audit(
        `${action.toUpperCase()}_COMPLETE`, room, version
      );
    } else {
      vscode.window.showErrorMessage(
        `❌ ${action} failed for ${room}. Check output panel.`
      );
      this.bridge.audit(
        `${action.toUpperCase()}_FAILED`, room, version
      );
    }

    this.roomTree.refresh();
  }

  // ── Utility ─────────────────────────────────────────────────

  private register(
    id:      string,
    handler: (...args: unknown[]) => unknown
  ): void {
    this.context.subscriptions.push(
      vscode.commands.registerCommand(id, handler)
    );
  }
}
