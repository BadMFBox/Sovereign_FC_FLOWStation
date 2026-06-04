// ═══════════════════════════════════════════════════════════════
//  AuditTreeView.ts
//  Live audit trail tree — every event, grouped by session
//  AiZQuad FlowStation Lab
// ═══════════════════════════════════════════════════════════════

import * as vscode        from "vscode";
import * as fs            from "fs";
import * as path          from "path";
import { BridgeConnector } from "./BridgeConnector";
import { SessionManager }  from "./SessionManager";

// ── Data model ──────────────────────────────────────────────────

interface AuditEntry {
  timestamp: string;
  event:     string;
  room:      string;
  detail:    string;
  source:    string;
}

interface AuditGroup {
  date:    string;       // "2024-01-15"
  entries: AuditEntry[];
}

// ── Tree Items ───────────────────────────────────────────────────

class AuditGroupItem extends vscode.TreeItem {
  constructor(
    public readonly group: AuditGroup
  ) {
    super(
      group.date,
      vscode.TreeItemCollapsibleState.Expanded
    );

    this.contextValue = "auditGroup";
    this.description  = `${group.entries.length} event(s)`;
    this.iconPath     = new vscode.ThemeIcon(
      "calendar",
      new vscode.ThemeColor("charts.blue")
    );
    this.tooltip      = `${group.entries.length} events on ${group.date}`;
  }
}

class AuditEntryItem extends vscode.TreeItem {
  constructor(
    public readonly entry: AuditEntry
  ) {
    super(
      AuditEntryItem.formatLabel(entry),
      vscode.TreeItemCollapsibleState.None
    );

    this.contextValue = "auditEntry";
    this.description  = entry.room || "system";
    this.iconPath     = new vscode.ThemeIcon(
      AuditEntryItem.iconForEvent(entry.event),
      new vscode.ThemeColor(
        AuditEntryItem.colorForEvent(entry.event)
      )
    );
    this.tooltip      = new vscode.MarkdownString(
      `**${entry.event}**\n\n` +
      `Room: \`${entry.room || "system"}\`\n\n` +
      (entry.detail ? `Detail: ${entry.detail}\n\n` : "") +
      `Time: ${entry.timestamp}\n\n` +
      `Source: ${entry.source}`
    );
  }

  // ── Helpers ────────────────────────────────────────────────

  static formatLabel(entry: AuditEntry): string {
    // "14:32:05  LOCK_COMPLETE"
    const time = entry.timestamp.slice(11, 19);
    return `${time}  ${entry.event}`;
  }

  static iconForEvent(event: string): string {
    const map: Record<string, string> = {
      // Session
      SESSION_UNLOCKED:        "unlock",
      SESSION_LOCKED:          "lock",
      SESSION_EXPIRED:         "clock",
      SESSION_UNLOCK_FAILED:   "error",
      // Lock
      LOCK_COMPLETE:           "lock",
      LOCK_FAILED:             "error",
      // Split
      SPLIT_COMPLETE:          "split-horizontal",
      SPLIT_FAILED:            "error",
      // Sort
      SORT_COMPLETE:           "list-ordered",
      SORT_FAILED:             "error",
      // Integrate
      INTEGRATE_COMPLETE:      "merge",
      INTEGRATE_FAILED:        "error",
      // Verify
      VERIFY_COMPLETE:         "shield",
      VERIFY_FAILED:           "warning",
      // Dialog
      DIALOG_STARTED:          "comment-discussion",
      DIALOG_PAUSED:           "debug-pause",
      DIALOG_ABORTED:          "circle-slash",
      DIALOG_COMPLETE:         "check",
      // AI
      AI_ACCESS_GRANTED:       "eye",
      AI_ACCESS_REVOKED:       "eye-closed",
      // Generic
      DEFAULT:                 "history",
    };
    return map[event] ?? map.DEFAULT;
  }

  static colorForEvent(event: string): string {
    if (event.endsWith("_FAILED"))   return "charts.red";
    if (event.endsWith("_COMPLETE")) return "charts.green";
    if (event.includes("SESSION"))   return "charts.blue";
    if (event.includes("DIALOG"))    return "charts.purple";
    if (event.includes("AI_"))       return "charts.yellow";
    if (event.includes("WARNING"))   return "charts.orange";
    return "charts.foreground";
  }
}

class AuditEmptyItem extends vscode.TreeItem {
  constructor(message: string) {
    super(message, vscode.TreeItemCollapsibleState.None);
    this.iconPath = new vscode.ThemeIcon(
      "info",
      new vscode.ThemeColor("charts.foreground")
    );
  }
}

// ── Tree Provider ────────────────────────────────────────────────

export class AuditTreeView
  implements vscode.TreeDataProvider<vscode.TreeItem> {

  private _onDidChangeTreeData =
    new vscode.EventEmitter<vscode.TreeItem | undefined>();

  readonly onDidChangeTreeData =
    this._onDidChangeTreeData.event;

  // Cached groups — rebuilt on refresh
  private groups: AuditGroup[] = [];

  // File watcher — auto-refresh on audit.log change
  private watcher: fs.FSWatcher | null = null;

  constructor(
    private bridge:  BridgeConnector,
    private session: SessionManager
  ) {
    session.on("unlocked", () => this.refresh());
    session.on("locked",   () => this.refresh());

    // Watch audit.log for live updates
    this.watchAuditLog();
  }

  // ── Public API ───────────────────────────────────────────────

  refresh(): void {
    this.groups = [];
    this._onDidChangeTreeData.fire(undefined);
  }

  getTreeItem(
    element: vscode.TreeItem
  ): vscode.TreeItem {
    return element;
  }

  async getChildren(
    element?: vscode.TreeItem
  ): Promise<vscode.TreeItem[]> {

    // Root — show locked message or date groups
    if (!element) {
      return this.getRootItems();
    }

    // Date group — show entries
    if (element instanceof AuditGroupItem) {
      return this.getGroupEntries(element.group);
    }

    return [];
  }

  // ── Private ──────────────────────────────────────────────────

  private getRootItems(): vscode.TreeItem[] {
    if (!this.session.isUnlocked()) {
      return [
        new AuditEmptyItem("🔒 Unlock to view audit trail")
      ];
    }

    // Load and group
    const entries = this.loadEntries();

    if (entries.length === 0) {
      return [new AuditEmptyItem("No audit events yet")];
    }

    this.groups = this.groupByDate(entries);
    return this.groups.map(g => new AuditGroupItem(g));
  }

  private getGroupEntries(
    group: AuditGroup
  ): vscode.TreeItem[] {
    // Most recent first within group
    return [...group.entries]
      .reverse()
      .map(e => new AuditEntryItem(e));
  }

  private loadEntries(): AuditEntry[] {
    const raw = this.bridge.getRecentAuditRaw(200);

    return raw.map(line => {
      try {
        return JSON.parse(line) as AuditEntry;
      } catch {
        // Malformed line — create a generic entry
        return {
          timestamp: new Date().toISOString(),
          event:     "RAW_LOG",
          room:      "system",
          detail:    line,
          source:    "unknown",
        };
      }
    });
  }

  private groupByDate(entries: AuditEntry[]): AuditGroup[] {
    const map = new Map<string, AuditEntry[]>();

    for (const entry of entries) {
      const date = entry.timestamp.slice(0, 10); // "2024-01-15"
      const existing = map.get(date) ?? [];
      existing.push(entry);
      map.set(date, existing);
    }

    // Sort dates newest first
    return Array.from(map.entries())
      .sort(([a], [b]) => b.localeCompare(a))
      .map(([date, entries]) => ({ date, entries }));
  }

  private watchAuditLog(): void {
    const logPath = this.bridge.getAuditLogPath();
    if (!fs.existsSync(logPath)) return;

    try {
      this.watcher = fs.watch(logPath, () => {
        // Debounce — only refresh once per 500ms burst
        if (this._refreshTimeout) {
          clearTimeout(this._refreshTimeout);
        }
        this._refreshTimeout = setTimeout(() => {
          this.refresh();
        }, 500);
      });
    } catch {
      // File watching not critical — fail silently
    }
  }

  private _refreshTimeout: ReturnType<typeof setTimeout> | null = null;

  dispose(): void {
    this.watcher?.close();
    this._onDidChangeTreeData.dispose();
    if (this._refreshTimeout) {
      clearTimeout(this._refreshTimeout);
    }
  }
}
