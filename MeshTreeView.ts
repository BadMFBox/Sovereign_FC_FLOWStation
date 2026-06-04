// ═══════════════════════════════════════════════════════════════
//  MeshTreeView.ts
//  Mesh integration tree — shows the wired room network
//  AiZQuad FlowStation Lab
// ═══════════════════════════════════════════════════════════════

import * as vscode        from "vscode";
import * as fs            from "fs";
import * as path          from "path";
import { BridgeConnector } from "./BridgeConnector";
import { SessionManager }  from "./SessionManager";

// ── Data model ───────────────────────────────────────────────────

interface MeshNode {
  room:        string;
  version:     string;
  status:      "integrated" | "pending" | "failed" | "sealed";
  connections: string[];    // other rooms this node links to
  lockedAt:    string | null;
  integratedAt: string | null;
  fileCount:   number;
  lockHash:    string | null;
}

interface MeshSummary {
  totalNodes:      number;
  integratedCount: number;
  pendingCount:    number;
  failedCount:     number;
  sealedCount:     number;
  lastActivity:    string | null;
}

// ── Tree Items ────────────────────────────────────────────────────

class MeshSummaryItem extends vscode.TreeItem {
  constructor(summary: MeshSummary) {
    super(
      "Mesh Overview",
      vscode.TreeItemCollapsibleState.None
    );

    const allGood = summary.failedCount === 0;

    this.contextValue = "meshSummary";
    this.description  =
      `${summary.integratedCount}/${summary.totalNodes} integrated`;
    this.iconPath     = new vscode.ThemeIcon(
      allGood ? "circuit-board" : "warning",
      new vscode.ThemeColor(
        allGood ? "charts.green" : "charts.orange"
      )
    );
    this.tooltip      = new vscode.MarkdownString(
      `**Mesh Status**\n\n` +
      `✅ Integrated: ${summary.integratedCount}\n\n` +
      `⏳ Pending:    ${summary.pendingCount}\n\n` +
      `❌ Failed:     ${summary.failedCount}\n\n` +
      `🔒 Sealed:     ${summary.sealedCount}\n\n` +
      (summary.lastActivity
        ? `Last activity: ${summary.lastActivity}`
        : "No activity yet"
      )
    );
  }
}

class MeshStatusSection extends vscode.TreeItem {
  constructor(
    label:    string,
    count:    number,
    icon:     string,
    color:    string,
    public readonly statusFilter: MeshNode["status"]
  ) {
    super(
      label,
      count > 0
        ? vscode.TreeItemCollapsibleState.Expanded
        : vscode.TreeItemCollapsibleState.None
    );

    this.contextValue = "meshSection";
    this.description  = `${count} room(s)`;
    this.iconPath     = new vscode.ThemeIcon(
      icon,
      new vscode.ThemeColor(color)
    );
  }
}

class MeshNodeItem extends vscode.TreeItem {
  constructor(
    public readonly node: MeshNode
  ) {
    super(
      node.room,
      node.connections.length > 0
        ? vscode.TreeItemCollapsibleState.Collapsed
        : vscode.TreeItemCollapsibleState.None
    );

    this.contextValue = "meshNode";
    this.description  = `@ ${node.version}`;
    this.iconPath     = new vscode.ThemeIcon(
      MeshNodeItem.iconForStatus(node.status),
      new vscode.ThemeColor(
        MeshNodeItem.colorForStatus(node.status)
      )
    );
    this.tooltip      = new vscode.MarkdownString(
      `**${node.room}**\n\n` +
      `Status:  ${MeshNodeItem.labelForStatus(node.status)}\n\n` +
      `Version: \`${node.version}\`\n\n` +
      `Files:   ${node.fileCount}\n\n` +
      (node.lockedAt
        ? `Locked:  ${node.lockedAt.slice(0, 19).replace("T", " ")}\n\n`
        : ""
      ) +
      (node.integratedAt
        ? `Integrated: ${node.integratedAt.slice(0, 19).replace("T", " ")}\n\n`
        : ""
      ) +
      (node.lockHash
        ? `Hash: \`${node.lockHash.slice(0, 12)}...\`\n\n`
        : ""
      ) +
      (node.connections.length > 0
        ? `Connections: ${node.connections.join(", ")}`
        : "No connections yet"
      )
    );
  }

  static iconForStatus(status: MeshNode["status"]): string {
    const map: Record<MeshNode["status"], string> = {
      integrated: "check",
      pending:    "circle-outline",
      failed:     "error",
      sealed:     "lock",
    };
    return map[status];
  }

  static colorForStatus(status: MeshNode["status"]): string {
    const map: Record<MeshNode["status"], string> = {
      integrated: "charts.green",
      pending:    "charts.yellow",
      failed:     "charts.red",
      sealed:     "charts.blue",
    };
    return map[status];
  }

  static labelForStatus(status: MeshNode["status"]): string {
    const map: Record<MeshNode["status"], string> = {
      integrated: "✅ Integrated",
      pending:    "⏳ Pending",
      failed:     "❌ Failed",
      sealed:     "🔒 Sealed",
    };
    return map[status];
  }
}

class MeshConnectionItem extends vscode.TreeItem {
  constructor(
    targetRoom:  string,
    sourceRoom:  string
  ) {
    super(
      `→ ${targetRoom}`,
      vscode.TreeItemCollapsibleState.None
    );

    this.contextValue = "meshConnection";
    this.description  = "linked";
    this.iconPath     = new vscode.ThemeIcon(
      "arrow-right",
      new vscode.ThemeColor("charts.blue")
    );
    this.tooltip      =
      `${sourceRoom} is connected to ${targetRoom} in the mesh`;
  }
}

class MeshDetailItem extends vscode.TreeItem {
  constructor(label: string, value: string, icon: string) {
    super(label, vscode.TreeItemCollapsibleState.None);
    this.description = value;
    this.iconPath    = new vscode.ThemeIcon(icon);
  }
}

class MeshEmptyItem extends vscode.TreeItem {
  constructor(message: string) {
    super(message, vscode.TreeItemCollapsibleState.None);
    this.iconPath = new vscode.ThemeIcon(
      "info",
      new vscode.ThemeColor("charts.foreground")
    );
  }
}

// ── Tree Provider ────────────────────────────────────────────────

export class MeshTreeView
  implements vscode.TreeDataProvider<vscode.TreeItem> {

  private _onDidChangeTreeData =
    new vscode.EventEmitter<vscode.TreeItem | undefined>();

  readonly onDidChangeTreeData =
    this._onDidChangeTreeData.event;

  // Cached nodes — rebuilt on refresh
  private nodes: MeshNode[] = [];

  constructor(
    private bridge:  BridgeConnector,
    private session: SessionManager
  ) {
    session.on("unlocked", () => this.refresh());
    session.on("locked",   () => this.refresh());
  }

  // ── Public API ───────────────────────────────────────────────

  refresh(): void {
    this.nodes = [];
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

    // Root — summary + status sections
    if (!element) {
      return this.getRootItems();
    }

    // Section — show filtered nodes
    if (element instanceof MeshStatusSection) {
      return this.getSectionNodes(element.statusFilter);
    }

    // Node — show connections + details
    if (element instanceof MeshNodeItem) {
      return this.getNodeChildren(element.node);
    }

    return [];
  }

  // ── Private ──────────────────────────────────────────────────

  private getRootItems(): vscode.TreeItem[] {
    if (!this.session.isUnlocked()) {
      return [
        new MeshEmptyItem("🔒 Unlock to view mesh")
      ];
    }

    // Load mesh nodes
    this.nodes = this.loadMeshNodes();

    if (this.nodes.length === 0) {
      return [
        new MeshEmptyItem("No rooms in mesh yet"),
        new MeshEmptyItem("Run integrate on a room to add it"),
      ];
    }

    // Build summary
    const summary = this.buildSummary(this.nodes);

    const items: vscode.TreeItem[] = [
      new MeshSummaryItem(summary),
    ];

    // Status sections — only show non-empty ones
    const sections: Array<{
      status:  MeshNode["status"];
      label:   string;
      icon:    string;
      color:   string;
    }> = [
      {
        status: "integrated",
        label:  "Integrated",
        icon:   "check-all",
        color:  "charts.green",
      },
      {
        status: "sealed",
        label:  "Sealed",
        icon:   "lock",
        color:  "charts.blue",
      },
      {
        status: "pending",
        label:  "Pending",
        icon:   "circle-outline",
        color:  "charts.yellow",
      },
      {
        status: "failed",
        label:  "Failed",
        icon:   "error",
        color:  "charts.red",
      },
    ];

    for (const s of sections) {
      const count = this.nodes.filter(
        n => n.status === s.status
      ).length;

      if (count > 0) {
        items.push(
          new MeshStatusSection(
            s.label, count, s.icon, s.color, s.status
          )
        );
      }
    }

    return items;
  }

  private getSectionNodes(
    filter: MeshNode["status"]
  ): vscode.TreeItem[] {
    return this.nodes
      .filter(n => n.status === filter)
      .map(n => new MeshNodeItem(n));
  }

  private getNodeChildren(
    node: MeshNode
  ): vscode.TreeItem[] {
    const items: vscode.TreeItem[] = [];

    // Connections
    if (node.connections.length > 0) {
      items.push(
        new MeshDetailItem(
          "Connections",
          `${node.connections.length}`,
          "plug"
        )
      );
      for (const conn of node.connections) {
        items.push(
          new MeshConnectionItem(conn, node.room)
        );
      }
    }

    // Details
    items.push(
      new MeshDetailItem("Version",   node.version,          "tag")
    );
    items.push(
      new MeshDetailItem("Files",     `${node.fileCount}`,   "files")
    );

    if (node.lockedAt) {
      items.push(
        new MeshDetailItem(
          "Locked",
          node.lockedAt.slice(0, 19).replace("T", " "),
          "lock"
        )
      );
    }

    if (node.integratedAt) {
      items.push(
        new MeshDetailItem(
          "Integrated",
          node.integratedAt.slice(0, 19).replace("T", " "),
          "merge"
        )
      );
    }

    if (node.lockHash) {
      items.push(
        new MeshDetailItem(
          "Hash",
          node.lockHash.slice(0, 16) + "...",
          "key"
        )
      );
    }

    return items;
  }

  // ── Data loading ─────────────────────────────────────────────

  private loadMeshNodes(): MeshNode[] {
    const meshDir   = this.bridge.getMeshDir();
    const lockedDir = this.bridge.getLockedDir();
    const activeDir = this.bridge.getActiveDir();

    if (!fs.existsSync(activeDir)) return [];

    const rooms = fs.readdirSync(activeDir).filter(f =>
      fs.statSync(path.join(activeDir, f)).isDirectory()
    );

    return rooms.map(room => {
      const isLocked     = fs.existsSync(path.join(lockedDir, room));
      const isIntegrated = fs.existsSync(path.join(meshDir, room));

      // Read mesh manifest if it exists
      const manifestPath = path.join(
        meshDir, room, "mesh.manifest.json"
      );
      let manifest: Partial<MeshNode> = {};
      if (fs.existsSync(manifestPath)) {
        try {
          manifest = JSON.parse(
            fs.readFileSync(manifestPath, "utf8")
          );
        } catch {
          // Corrupt manifest — continue with defaults
        }
      }

      // Read lock info
      const lockInfoPath = path.join(
        lockedDir, room, "lock.info.json"
      );
      let lockInfo: {
        version?:  string;
        lockedAt?: string;
        hash?:     string;
      } = {};
      if (fs.existsSync(lockInfoPath)) {
        try {
          lockInfo = JSON.parse(
            fs.readFileSync(lockInfoPath, "utf8")
          );
        } catch {
          // Non-fatal
        }
      }

      // Determine status
      let status: MeshNode["status"] = "pending";
      if (isIntegrated && isLocked) status = "sealed";
      else if (isIntegrated)        status = "integrated";
      else if (!isLocked)           status = "pending";

      // Check for failed state
      const failPath = path.join(meshDir, room, ".failed");
      if (fs.existsSync(failPath))  status = "failed";

      return {
        room,
        version:      lockInfo.version ?? manifest.version ?? "unknown",
        status,
        connections:  (manifest.connections as string[]) ?? [],
        lockedAt:     lockInfo.lockedAt   ?? null,
        integratedAt: (manifest.integratedAt as string) ?? null,
        fileCount:    this.bridge.getRoomFileCount(room),
        lockHash:     lockInfo.hash       ?? null,
      };
    });
  }

  private buildSummary(nodes: MeshNode[]): MeshSummary {
    const counts = nodes.reduce(
      (acc, n) => {
        acc[n.status] = (acc[n.status] ?? 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );

    // Find most recent activity from audit log
    const recentAudit = this.bridge.getRecentAuditRaw(10);
    let lastActivity: string | null = null;

    for (const line of recentAudit) {
      try {
        const entry = JSON.parse(line);
        if (
          entry.event.includes("INTEGRATE") ||
          entry.event.includes("LOCK")
        ) {
          lastActivity = entry.timestamp.slice(0, 19).replace("T", " ");
          break;
        }
      } catch {
        // Skip
      }
    }

    return {
      totalNodes:      nodes.length,
      integratedCount: counts["integrated"] ?? 0,
      pendingCount:    counts["pending"]    ?? 0,
      failedCount:     counts["failed"]     ?? 0,
      sealedCount:     counts["sealed"]     ?? 0,
      lastActivity,
    };
  }

  dispose(): void {
    this._onDidChangeTreeData.dispose();
  }
}
