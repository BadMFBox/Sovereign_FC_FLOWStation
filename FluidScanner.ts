// ═══════════════════════════════════════════════════════════════
//  FluidScanner.ts
//  Scans your room, labels what it sees, shows you the map
// ═══════════════════════════════════════════════════════════════

import * as fs   from "fs";
import * as path from "path";
import { TerminalBridge } from "./TerminalBridge";

// Pattern-based labeling — no AI needed for basics
// Fast, local, private, zero API calls
const FLUID_PATTERNS: Record<string, RegExp[]> = {
  auth:       [/auth/i,    /login/i,   /session/i, /token/i,  /pin/i    ],
  core:       [/core/i,    /base/i,    /main/i,    /engine/i, /flow/i   ],
  config:     [/config/i,  /settings/i,/env/i,     /setup/i              ],
  model:      [/model/i,   /schema/i,  /entity/i,  /struct/i             ],
  api:        [/api/i,     /route/i,   /endpoint/i,/handler/i            ],
  validation: [/valid/i,   /check/i,   /verify/i,  /guard/i              ],
  util:       [/util/i,    /helper/i,  /tool/i,    /format/i, /parse/i  ],
  mesh:       [/mesh/i,    /surface/i, /wire/i,    /bridge/i, /lock/i   ],
};

// Phase suggestion based on type
const PHASE_MAP: Record<string, string> = {
  auth:       "LOCK → INTEGRATE",
  core:       "SPLIT → SORT",
  config:     "LOCK",
  model:      "SPLIT",
  api:        "SPLIT → SORT → INTEGRATE",
  validation: "SORT",
  util:       "SORT",
  mesh:       "INTEGRATE",
};

export class FluidScanner {

  constructor(private bridge: TerminalBridge) {}

  /**
   * Scan a room and return fluid tags.
   * Local pattern matching — no API calls.
   * Fast. Private. Always yours.
   */
  scan(roomPath: string, room: string): FluidScan {
    const files: FluidFile[] = [];

    // Walk the room directory
    const allFiles = this.walk(roomPath);

    for (const filePath of allFiles) {
      const raw     = path.basename(filePath);
      const content = fs.readFileSync(filePath, "utf8");
      const tag     = this.detectTag(raw, content);
      const flow    = PHASE_MAP[tag.type] ?? "SPLIT";
      const notes   = this.observeFile(content, tag.type);

      files.push({ path: filePath, raw, tag, flow, notes });
    }

    return {
      room,
      scannedAt: new Date().toISOString(),
      files,
      summary:   this.buildSummary(files),
      userOwns:  true,
    };
  }

  /**
   * Detect what a file is based on name + content patterns.
   * Always a suggestion. Never a command.
   */
  private detectTag(filename: string, content: string): FluidTag {
    const scores: Record<string, number> = {};

    for (const [type, patterns] of Object.entries(FLUID_PATTERNS)) {
      scores[type] = 0;
      for (const pattern of patterns) {
        if (pattern.test(filename)) scores[type] += 2; // name match = stronger
        if (pattern.test(content))  scores[type] += 1; // content match
      }
    }

    // Pick highest score
    const best = Object.entries(scores).sort((a, b) => b[1] - a[1])[0];
    const [type, score] = best;

    // Confidence based on score
    const maxPossible  = 3 * (FLUID_PATTERNS[type]?.length ?? 1);
    const confidence   = Math.min(score / maxPossible, 1.0);

    // Human-readable label
    const name = this.buildLabel(filename, type);

    return {
      name,
      type,
      confidence,
      suggested: true,
      confirmed: false,     // YOU confirm, not AI
    };
  }

  /**
   * Build a clean readable label for the file.
   * Like Mixplorer — just makes it readable.
   */
  private buildLabel(filename: string, type: string): string {
    // Strip extension
    const base = filename.replace(/\.(py|ts|js|cpp|h)$/, "");

    // Clean up underscores/dashes
    const clean = base
      .replace(/[_-]/g, " ")
      .replace(/([A-Z])/g, " $1")
      .trim()
      .toLowerCase();

    // Capitalize first word
    const titled = clean.charAt(0).toUpperCase() + clean.slice(1);

    return `[${type.toUpperCase()}] ${titled}`;
  }

  /**
   * Non-invasive observations about the file.
   * Observations — not instructions.
   */
  private observeFile(content: string, type: string): string[] {
    const notes: string[] = [];
    const lines = content.split("\n").length;

    // Size observations
    if (lines > 300) notes.push(`Large file (${lines} lines) — consider splitting`);
    if (lines < 10)  notes.push("Very small — may be a stub or placeholder");

    // Type-specific observations
    if (type === "auth") {
      if (/password/i.test(content) && !/hash/i.test(content)) {
        notes.push("Password handling detected — verify hashing");
      }
      if (/token/i.test(content)) {
        notes.push("Token logic present");
      }
    }

    if (type === "api") {
      const endpoints = (content.match(/route|endpoint|@app\.|@router\./gi) ?? []).length;
      if (endpoints > 0) notes.push(`~${endpoints} endpoint(s) detected`);
    }

    if (type === "config") {
      if (/os\.environ|process\.env/i.test(content)) {
        notes.push("Environment variables in use");
      }
    }

    if (type === "core") {
      const classes = (content.match(/^class /gm) ?? []).length;
      if (classes > 0) notes.push(`${classes} class(es) found`);
    }

    return notes;
  }

  /**
   * Build a human-readable summary of the scan.
   */
  private buildSummary(files: FluidFile[]): string {
    const counts: Record<string, number> = {};
    for (const f of files) {
      counts[f.tag.type] = (counts[f.tag.type] ?? 0) + 1;
    }

    const parts = Object.entries(counts)
      .map(([type, count]) => `${count} ${type}`)
      .join(", ");

    return `${files.length} file(s) scanned: ${parts}`;
  }

  /**
   * Walk a directory recursively.
   */
  private walk(dir: string): string[] {
    const results: string[] = [];
    if (!fs.existsSync(dir)) return results;

    for (const entry of fs.readdirSync(dir)) {
      const full = path.join(dir, entry);
      const stat = fs.statSync(full);

      if (stat.isDirectory()) {
        results.push(...this.walk(full));
      } else if (/\.(py|ts|js|cpp|h)$/.test(entry)) {
        results.push(full);
      }
    }
    return results;
  }
}
