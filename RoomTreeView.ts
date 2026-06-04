// ═══════════════════════════════════════════════════════════════
//  RoomTreeView.ts
//  Room explorer tree — see all rooms, states, and actions
// ═══════════════════════════════════════════════════════════════

import * as vscode       from "vscode";
import * as path         from "path";
import { BridgeConnector } from "./BridgeConnector";
import { SessionManager }  from "./SessionManager";

// ── Tree item types ─────────────────────────────────────────────

export class RoomItem extends vscode.TreeItem {
  constructor(
    public readonly roomName: string,
    public readonly isLocked: boolean,
    public readonly fileCount: number,
    public readonly version:   string | null
  ) {
    super(roomName, vscode.TreeItemCollapsibleState.Collapsed);

    this.contextValue   = "room";
    this.description    = isLocked
      ? `🔒 ${version ?? "locked"}`
      : `${fileCount} file(s)`;
    this.tooltip        = new vscode.MarkdownString(
      `**${roomName}**\n\n` +
      `Status: ${isLocked ? "🔒 Locked" : "🔓 Active"}\n` +
      `Files: ${fileCount}\n` +
      (version ? `Version: ${version}\n` : "") +
      `\n*Right-click for actions*`
    );
    this.iconPath       = new vscode.ThemeIcon(
      isLocked ? "lock" : "folder-opened",
      new vscode.ThemeColor(
        isLocked
          ? "charts.yellow"
          : "charts.green"
      )
    );
  }
}

export class RoomFileItem extends vscode.TreeItem {
  constructor(
    public readonly filename: string,
    public readonly filePath: string,
    public readonly tag:      string,
    public readonly tagType:  string
  ) {
    super(filename, vscode.TreeItemCollapsibleState.None);

    this.contextValue = "roomFile";
    this.description  = tag;
    this.tooltip      = `${filePath}\nType: ${tagType}`;
    this.iconPath     = new vscode.ThemeIcon(
      this.iconForType(tagType)
    );
    this.command      = {
      command:   "vscode.open",
      title:     "Open File",
      arguments: [vscode.Uri.file(filePath)]
    };
  }

  private iconForType(type: string): string {
    const icons: Record<string, string> = {
      auth:       "shield",
      core:       "symbol-class",
      config:     "gear",
      api:        "cloud",
      model:      "symbol-structure",
      util:       "symbol-method",
      mesh:       "circuit-board",
      validation: "pass",
    };
    return icons[type] ?? "file-code";
  }
}

export class PhaseItem extends vscode.TreeItem {
  constructor(
    label:     string,
    completed: boolean
  ) {
    super(label, vscode.TreeItemCollapsibleState.None);
    this.iconPath = new vscode.ThemeIcon(
      completed ? "check" : "circle-outline",
      new vscode.ThemeColor(
        completed ? "charts.green" : "charts.gray"
      )
    );
  }
}

// ── Tree Provider ───────────────────────────────────────────────

export class RoomTreeView
  implements vscode.TreeDataProvider<vscode.TreeItem> {

  private _onDidChangeTreeData =
    new vscode.EventEmitter<vscode.TreeItem | undefined>();

  readonly onDidChangeTreeData =
    this._onDidChangeTreeData.event;

  constructor(
    private bridge:  BridgeConnector,
    private session: SessionManager
  ) {
    session.on("unlocked", () => this.refresh());
    session.on("locked",   () => this.refresh());
  }

  refresh(): void {
    this._onDidChangeTreeData.fire(undefined);
  }

  getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(
    element?: vscode.TreeItem
  ): Promise<vscode.TreeItem[]> {

    // Root — show all rooms
    if (!element) {
      return this.getRooms();
    }

    // Room — show files + phase status
    if (element instanceof RoomItem) {
      return this.getRoomChildren(element.roomName);
    }

    return [];
  }

  // ── Private ─────────────────────────────────────────────────

  private async getRooms(): Promise<vscode.TreeItem[]> {
    if (!this.session.isUnlocked()) {
      return [
        Object.assign(
          new vscode.TreeItem("🔒 Session locked"),
          {
            command: {
              command: "flowstation.unlock",
              title:   "Unlock"
            },
            tooltip: "Click to unlock FlowStation"
          }
        )
      ];
    }

    const rooms = this.bridge.listActiveRooms();

    if (rooms.length === 0) {
      return [
        new vscode.TreeItem(
          "No rooms found in forge/active/"
        )
      ];
    }

    return rooms.map(room => {
      const locked    = this.bridge.isRoomLocked(room);
      const fileCount = this.bridge.getRoomFileCount(room);
      const version   = this.bridge.getLatestVersion(room);

      return new RoomItem(room, locked, fileCount, version);
    });
  }

  private async getRoomChildren(
    room: string
  ): Promise<vscode.TreeItem[]> {
    const items: vscode.TreeItem[] = [];

    // ── Phase status section ──────────────────────────────
    const phases = this.bridge.getRoomPhases(room);

    items.push(
      Object.assign(
        new vscode.TreeItem(
          "Phases",
          vscode.TreeItemCollapsibleState.None
        ),
        { description: "", iconPath: new vscode.ThemeIcon("list-ordered") }
      )
    );

    items.push(new PhaseItem("🔒 Lock",      phases.locked));
    items.push(new PhaseItem("✂️  Split",     phases.split));
    items.push(new PhaseItem("🗂  Sort",      phases.sorted));
    items.push(new PhaseItem("🔗 Integrate", phases.integrated));

    // ── Files section ─────────────────────────────────────
    const files = this.bridge.scanRoomFiles(room);

    if (files.length > 0) {
      items.push(
        Object.assign(
          new vscode.TreeItem(
            "Files",
            vscode.TreeItemCollapsibleState.None
          ),
          {
            description:  `${files.length} file(s)`,
            iconPath: new vscode.ThemeIcon("folder")
          }
        )
      );

      for (const file of files) {
        items.push(
          new RoomFileItem(
            file.filename,
            file.path,
            file.tag.name,
            file.tag.type
          )
        );
      }
    }

    return items;
  }
}
