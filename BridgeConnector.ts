// ═══════════════════════════════════════════════════════════════
//  BridgeConnector.ts
//  Connects the VS Code extension to the TerminalBridge
//  Wraps all shell calls and file reads safely
// ═══════════════════════════════════════════════════════════════

import * as vscode from "vscode";
import * as cp     from "child_process";
import * as fs     from "fs";
import * as path   from "path";

export interface RoomFile {
  filename: string;
  path:     string;
  tag: {
    name:       string;
    type:       string;
    confidence: number;
  };
}

export interface RoomPhases {
  locked:     boolean;
  split:      boolean;
  sorted:     boolean;
  integrated: boolean;
}

export class BridgeConnector {

  constructor(private root: string) {}

  // ── Session ─────────────────────────────────────────────────

  async verifyPin(pin: string): Promise<boolean> {
    try {
      const result = this.run(`make verify-pin PIN="${pin}"`);
      return result.includes("PIN_OK");
    } catch {
      // Fallback: compare hashed PIN from config
      const configPath = path.join(this.root, "shared", "config.json");
      if (!fs.existsSync(configPath)) return false;
      const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
      const crypto = require("crypto");
      const hash   = crypto
        .createHash("sha256")
        .update(pin)
        .digest("hex");
      return config.pinHash === hash;
    }
  }

  // ── Rooms ────────────────────────────────────────────────────

  listActiveRooms(): string[] {
    const activeDir = path.join(this.root, "forge", "active");
    if (!fs.existsSync(activeDir)) return [];
    return fs.readdirSync(activeDir).filter(f =>
      fs.statSync(path.join(activeDir, f)).isDirectory()
    );
  }

  isRoomLocked(room: string): boolean {
    const lockPath = path.join(
      this.root, "forge", "locked", room
    );
    return fs.existsSync(lockPath);
  }

  getRoomFileCount(room: string): number {
    const roomDir = path.join(
      this.root, "forge", "active", room
    );
    if (!fs.existsSync(roomDir)) return 0;
    return fs.readdirSync(roomDir).filter(f =>
      fs.statSync(path.join(roomDir, f)).isFile()
    ).length;
  }

  getLatestVersion(room: string): string | null {
    const versionsDir = path.join(
      this.root, "forge", "versions", room
    );
    if (!fs.existsSync(versionsDir)) return null;
    const versions = fs.readdirSync(versionsDir).sort();
    return versions[versions.length - 1] ?? null;
  }

  getRoomPhases(room: string): RoomPhases {
    const check = (subdir: string) =>
      fs.existsSync(path.join(this.root, "forge", subdir, room));

    return {
      locked:     check("locked"),
      split:      check("split"),
      sorted:     check("sorted"),
      integrated: check("integrated"),
    };
  }

  scanRoomFiles(room: string): RoomFile[] {
    const roomDir = path.join(this.root, "forge", "active", room);
    if (!fs.existsSync(roomDir)) return [];

    return fs.readdirSync(roomDir)
      .filter(f => fs.statSync(path.join(roomDir, f)).isFile())
      .map(filename => ({
        filename,
        path: path.join(roomDir, filename),
        tag:  this.inferTag(filename),
      }));
  }

  // ── Actions ─────────────────────────────────────────────────

  async runAction(
    action:  string,
    room:    string,
    version: string,
    output:  vscode.OutputChannel
  ): Promise<boolean> {
    return new Promise(resolve => {
      const cmd  = `make ${action} ROOM=${room} VERSION=${version}`;
      const proc = cp.spawn("sh", ["-c", cmd], { cwd: this.root });

      proc.stdout.on("data", (d: Buffer) => {
        output.append(d.toString());
      });
      proc.stderr.on("data", (d: Buffer) => {
        output.append(d.toString());
      });
      proc.on("close", code => {
        resolve(code === 0);
      });
    });
  }

  // ── Audit ────────────────────────────────────────────────────

  audit(event: string, room: string, detail: string = ""): void {
    const logPath = path.join(this.root, "shared", "audit.log");
    const line    = JSON.stringify({
      timestamp: new Date().toISOString(),
      event,
      room,
      detail,
      source: "vscode-extension",
    }) + "\n";

    try {
      fs.appendFileSync(logPath, line, "utf8");
    } catch {
      // Audit failure is non-fatal
    }
  }

  getRecentAudit(limit = 20): string[] {
    const logPath = path.join(this.root, "shared", "audit.log");
    if (!fs.existsSync(logPath)) return [];

    const lines = fs.readFileSync(logPath, "utf8")
      .split("\n")
      .filter(Boolean)
      .slice(-limit)
      .reverse();

    return lines.map(line => {
      try {
        const entry = JSON.parse(line);
        return `${entry.timestamp.slice(0, 19).replace("T", " ")}  ${entry.event}  ${entry.room}`;
      } catch {
        return line;
      }
    });
  }

  // ── Private helpers ─────────────────────────────────────────

  private run(cmd: string): string {
    return cp.execSync(cmd, {
      cwd:      this.root,
      encoding: "utf8",
      timeout:  10_000,
    });
  }

  private inferTag(filename: string): RoomFile["tag"] {
    const lower = filename.toLowerCase();
    const rules: Array<[RegExp, string, string]> = [
      [/auth|session|token|login|jwt/,    "AUTH",   "auth"  ],
      [/config|settings|env|constants/,   "CONFIG", "config"],
      [/api|route|endpoint|handler/,      "API",    "api"   ],
      [/model|schema|entity|type/,        "MODEL",  "model" ],
      [/util|helper|common|shared/,       "UTIL",   "util"  ],
      [/mesh|bridge|connector|integrate/, "MESH",   "mesh"  ],
      [/valid|guard|check|assert/,        "VALID",  "validation"],
    ];

    for (const [pattern, name, type] of rules) {
      if (pattern.test(lower)) {
        return { name, type, confidence: 82 };
      }
    }

    return { name: "CORE", type: "core", confidence: 60 };
  }

  destroy(): void {
    // cleanup if needed
  }
}
