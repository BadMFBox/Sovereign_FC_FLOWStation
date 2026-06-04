// ═══════════════════════════════════════════════════════════════
//  AiZQuad Lab — FC_FLOW MESH
//  TerminalBridge.ts
//
//  TypeScript bridge between the UI layer and the Python pipeline.
//  Handles:
//    - Command execution (lock, split, sort, integrate)
//    - Session management (PIN, TTL, lock/unlock)
//    - AI access control (grant, revoke, check)
//    - Real-time output streaming
//    - Pipeline state tracking
//    - Audit log reading
//
//  Founder: Juan Jaime Rivera Zamorano
// ═══════════════════════════════════════════════════════════════

import { spawn, ChildProcess }     from "child_process";
import { EventEmitter }            from "events";
import * as fs                     from "fs";
import * as path                   from "path";
import * as readline               from "readline";
import * as crypto                 from "crypto";


// ───────────────────────────────────────────────────────────────
//  TYPES & INTERFACES
// ───────────────────────────────────────────────────────────────

export type PipelinePhase =
  | "LOCK"
  | "SPLIT"
  | "SORT"
  | "INTEGRATE"
  | "VERIFY"
  | "WIRE"
  | "SEAL";

export type AIAccessLevel = "surface" | "read" | "none";

export type CommandStatus =
  | "PENDING"
  | "RUNNING"
  | "SUCCESS"
  | "FAILED"
  | "TIMEOUT";

export type LogLevel = "INFO" | "WARN" | "ERROR" | "DEBUG" | "SUCCESS";

export interface BridgeConfig {
  workspaceRoot:   string;
  pythonBinary:    string;
  sessionTTLHours: number;
  maxPinAttempts:  number;
  logLevel:        LogLevel;
  commandTimeout:  number; // ms
}

export interface CommandResult {
  command:   string;
  status:    CommandStatus;
  stdout:    string;
  stderr:    string;
  exitCode:  number | null;
  duration:  number; // ms
  timestamp: string;
}

export interface PipelineState {
  lastRoom:      string | null;
  lastAction:    PipelinePhase | null;
  lastCompleted: PipelinePhase | null;
  lastFailed:    PipelinePhase | null;
  resumeFrom:    PipelinePhase | null;
  timestamp:     string;
}

export interface SessionState {
  active:     boolean;
  createdAt:  number;
  expiresAt:  number;
  ttlHours:   number;
}

export interface AIAccessRecord {
  level:     AIAccessLevel;
  grantedAt: string;
  active:    boolean;
}

export interface AIAccessMap {
  [room: string]: AIAccessRecord;
}

export interface LogEntry {
  ts:     string;
  action: string;
  room:   string;
  detail: string;
}

export interface MeshManifest {
  mesh_version: string;
  rooms:        string[];
  room_count:   number;
  status:       string;
  wired_at:     string;
}

export interface LockRecord {
  room:      string;
  version:   string;
  locked_at: string;
  locked_by: string;
  signature: string;
  files:     number;
  status:    string;
}

// ───────────────────────────────────────────────────────────────
//  TERMINAL BRIDGE EVENTS
// ───────────────────────────────────────────────────────────────

export interface TerminalBridgeEvents {
  // Command lifecycle
  "command:start":    (cmd: string) => void;
  "command:stdout":   (line: string) => void;
  "command:stderr":   (line: string) => void;
  "command:done":     (result: CommandResult) => void;
  "command:timeout":  (cmd: string) => void;
  "command:error":    (err: Error) => void;

  // Pipeline phases
  "pipeline:phase":   (phase: PipelinePhase, room: string) => void;
  "pipeline:success": (phase: PipelinePhase, room: string) => void;
  "pipeline:failed":  (phase: PipelinePhase, room: string, err: string) => void;
  "pipeline:done":    (room: string) => void;

  // Session
  "session:unlocked": () => void;
  "session:locked":   () => void;
  "session:expired":  () => void;
  "session:refresh":  () => void;

  // AI access
  "ai:granted":  (room: string, level: AIAccessLevel) => void;
  "ai:revoked":  (room: string) => void;
  "ai:denied":   (room: string, reason: string) => void;

  // Audit
  "audit:entry": (entry: LogEntry) => void;

  // Errors
  "error": (err: Error) => void;
}


// ───────────────────────────────────────────────────────────────
//  TERMINAL BRIDGE CLASS
// ───────────────────────────────────────────────────────────────

export class TerminalBridge extends EventEmitter {

  private config:          BridgeConfig;
  private activeProcess:   ChildProcess | null = null;
  private sessionTimer:    NodeJS.Timeout | null = null;
  private pinAttempts:     number = 0;

  // Computed paths from workspace root
  private readonly paths: {
    shared:      string;
    forge:       string;
    splitter:    string;
    sorter:      string;
    integration: string;
    mesh:        string;
    session:     string;
    pin:         string;
    aiAccess:    string;
    auditLog:    string;
    pipeState:   string;
  };

  // ──────────────────────────────────────────────────────────
  //  CONSTRUCTOR
  // ──────────────────────────────────────────────────────────

  constructor(config: Partial<BridgeConfig> = {}) {
    super();

    this.config = {
      workspaceRoot:   config.workspaceRoot   ?? process.cwd(),
      pythonBinary:    config.pythonBinary    ?? "python3",
      sessionTTLHours: config.sessionTTLHours ?? 4,
      maxPinAttempts:  config.maxPinAttempts  ?? 3,
      logLevel:        config.logLevel        ?? "INFO",
      commandTimeout:  config.commandTimeout  ?? 300_000, // 5 min default
    };

    // Precompute all paths once
    const root = this.config.workspaceRoot;
    this.paths = {
      shared:      path.join(root, "shared"),
      forge:       path.join(root, "forge"),
      splitter:    path.join(root, "splitter"),
      sorter:      path.join(root, "sorter"),
      integration: path.join(root, "integration"),
      mesh:        path.join(root, "integration", "output", "mesh"),
      session:     path.join(root, "shared", ".session"),
      pin:         path.join(root, "shared", ".pin"),
      aiAccess:    path.join(root, "shared", "ai_access.json"),
      auditLog:    path.join(root, "shared", "audit.log"),
      pipeState:   path.join(root, "shared", "pipeline_state.json"),
    };

    this.ensureDirectories();
    this.log("INFO", "TerminalBridge initialized", root);
  }


  // ──────────────────────────────────────────────────────────
  //  DIRECTORY SETUP
  // ──────────────────────────────────────────────────────────

  private ensureDirectories(): void {
    const dirs = [
      this.paths.shared,
      this.paths.forge,
      path.join(this.paths.forge, "active"),
      path.join(this.paths.forge, "locked"),
      path.join(this.paths.forge, "versions"),
      path.join(this.paths.splitter, "output"),
      path.join(this.paths.sorter, "input"),
      path.join(this.paths.sorter, "output"),
      path.join(this.paths.integration, "input"),
      path.join(this.paths.integration, "merge"),
      path.join(this.paths.integration, "logic_locks"),
      this.paths.mesh,
    ];

    for (const dir of dirs) {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    }
  }


  // ──────────────────────────────────────────────────────────
  //  COMMAND EXECUTION ENGINE
  // ──────────────────────────────────────────────────────────

  /**
   * Execute a shell command with full streaming output.
   * Emits real-time stdout/stderr events.
   */
  public async exec(
    command: string,
    args:    string[]  = [],
    options: {
      cwd?:     string;
      env?:     NodeJS.ProcessEnv;
      timeout?: number;
    } = {}
  ): Promise<CommandResult> {

    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      const stdout:   string[] = [];
      const stderr:   string[] = [];
      const timeout   = options.timeout ?? this.config.commandTimeout;

      this.log("DEBUG", `exec: ${command} ${args.join(" ")}`);
      this.emit("command:start", `${command} ${args.join(" ")}`);

      // Spawn the process
      const proc = spawn(command, args, {
        cwd:   options.cwd ?? this.config.workspaceRoot,
        env:   { ...process.env, ...options.env },
        shell: false, // never use shell: true (security)
      });

      this.activeProcess = proc;

      // Stream stdout line by line
      const stdoutRL = readline.createInterface({ input: proc.stdout });
      stdoutRL.on("line", (line: string) => {
        stdout.push(line);
        this.emit("command:stdout", line);
        this.log("DEBUG", `[stdout] ${line}`);
      });

      // Stream stderr line by line
      const stderrRL = readline.createInterface({ input: proc.stderr });
      stderrRL.on("line", (line: string) => {
        stderr.push(line);
        this.emit("command:stderr", line);
        this.log("WARN", `[stderr] ${line}`);
      });

      // Timeout guard
      const timer = setTimeout(() => {
        proc.kill("SIGTERM");
        this.emit("command:timeout", command);
        reject(new Error(`Command timed out after ${timeout}ms: ${command}`));
      }, timeout);

      // Process exit
      proc.on("close", (exitCode: number | null) => {
        clearTimeout(timer);
        this.activeProcess = null;

        const result: CommandResult = {
          command:   `${command} ${args.join(" ")}`,
          status:    exitCode === 0 ? "SUCCESS" : "FAILED",
          stdout:    stdout.join("\n"),
          stderr:    stderr.join("\n"),
          exitCode,
          duration:  Date.now() - startTime,
          timestamp: new Date().toISOString(),
        };

        this.emit("command:done", result);

        if (exitCode === 0) {
          resolve(result);
        } else {
          reject(
            new Error(
              `Command failed (exit ${exitCode}): ${command}\n${stderr.join("\n")}`
            )
          );
        }
      });

      proc.on("error", (err: Error) => {
        clearTimeout(timer);
        this.activeProcess = null;
        this.emit("command:error", err);
        reject(err);
      });
    });
  }

  /**
   * Run a Python script through the pipeline.
   */
  public async runPython(
    script:  string,
    args:    string[] = [],
    options: { cwd?: string; timeout?: number } = {}
  ): Promise<CommandResult> {
    return this.exec(
      this.config.pythonBinary,
      [script, ...args],
      options
    );
  }

  /**
   * Run a Makefile target.
   */
  public async runMake(
    target: string,
    vars:   Record<string, string> = {}
  ): Promise<CommandResult> {
    const varArgs = Object.entries(vars).map(([k, v]) => `${k}=${v}`);
    return this.exec("make", [target, ...varArgs]);
  }

  /**
   * Kill any running process immediately.
   */
  public kill(): void {
    if (this.activeProcess) {
      this.activeProcess.kill("SIGTERM");
      this.activeProcess = null;
      this.log("WARN", "Active process killed by user");
    }
  }


  // ──────────────────────────────────────────────────────────
  //  PIPELINE COMMANDS
  // ──────────────────────────────────────────────────────────

  /**
   * Phase 1 — Lock a room at a version.
   */
  public async lock(room: string, version: string): Promise<CommandResult> {
    this.emit("pipeline:phase", "LOCK", room);
    this.audit("LOCK_START", room, `version=${version}`);

    try {
      const result = await this.runMake("lock", { ROOM: room, VERSION: version });
      this.emit("pipeline:success", "LOCK", room);
      this.audit("LOCK_OK", room, `version=${version}`);
      await this.savePipelineState({
        lastRoom:      room,
        lastAction:    "LOCK",
        lastCompleted: "LOCK",
        lastFailed:    null,
        resumeFrom:    null,
        timestamp:     new Date().toISOString(),
      });
      return result;
    } catch (err) {
      const msg = (err as Error).message;
      this.emit("pipeline:failed", "LOCK", room, msg);
      this.audit("LOCK_FAIL", room, msg);
      await this.savePipelineState({
        lastRoom:      room,
        lastAction:    "LOCK",
        lastCompleted: null,
        lastFailed:    "LOCK",
        resumeFrom:    "LOCK",
        timestamp:     new Date().toISOString(),
      });
      throw err;
    }
  }

  /**
   * Phase 2 — Split a room into modules.
   */
  public async split(room: string): Promise<CommandResult> {
    this.emit("pipeline:phase", "SPLIT", room);
    this.audit("SPLIT_START", room, "");

    try {
      const result = await this.runMake("split", { ROOM: room });
      this.emit("pipeline:success", "SPLIT", room);
      this.audit("SPLIT_OK", room, "");
      await this.savePipelineState({
        lastRoom:      room,
        lastAction:    "SPLIT",
        lastCompleted: "SPLIT",
        lastFailed:    null,
        resumeFrom:    null,
        timestamp:     new Date().toISOString(),
      });
      return result;
    } catch (err) {
      const msg = (err as Error).message;
      this.emit("pipeline:failed", "SPLIT", room, msg);
      this.audit("SPLIT_FAIL", room, msg);
      await this.savePipelineState({
        lastRoom:      room,
        lastAction:    "SPLIT",
        lastCompleted: "LOCK",
        lastFailed:    "SPLIT",
        resumeFrom:    "SPLIT",
        timestamp:     new Date().toISOString(),
      });
      throw err;
    }
  }

  /**
   * Phase 3 — Sort modules into categories.
   */
  public async sort(room: string): Promise<CommandResult> {
    this.emit("pipeline:phase", "SORT", room);
    this.audit("SORT_START", room, "");

    try {
      const result = await this.runMake("sort", { ROOM: room });
      this.emit("pipeline:success", "SORT", room);
      this.audit("SORT_OK", room, "");
      await this.savePipelineState({
        lastRoom:      room,
        lastAction:    "SORT",
        lastCompleted: "SORT",
        lastFailed:    null,
        resumeFrom:    null,
        timestamp:     new Date().toISOString(),
      });
      return result;
    } catch (err) {
      const msg = (err as Error).message;
      this.emit("pipeline:failed", "SORT", room, msg);
      this.audit("SORT_FAIL", room, msg);
      await this.savePipelineState({
        lastRoom:      room,
        lastAction:    "SORT",
        lastCompleted: "SPLIT",
        lastFailed:    "SORT",
        resumeFrom:    "SORT",
        timestamp:     new Date().toISOString(),
      });
      throw err;
    }
  }

  /**
   * Phase 4 — Integrate into the mesh.
   */
  public async integrate(room: string): Promise<CommandResult> {
    this.emit("pipeline:phase", "INTEGRATE", room);
    this.audit("INTEGRATE_START", room, "");

    try {
      const result = await this.runMake("integrate", { ROOM: room });
      this.emit("pipeline:success", "INTEGRATE", room);
      this.audit("INTEGRATE_OK", room, "");
      await this.savePipelineState({
        lastRoom:      room,
        lastAction:    "INTEGRATE",
        lastCompleted: "INTEGRATE",
        lastFailed:    null,
        resumeFrom:    null,
        timestamp:     new Date().toISOString(),
      });
      return result;
    } catch (err) {
      const msg = (err as Error).message;
      this.emit("pipeline:failed", "INTEGRATE", room, msg);
      this.audit("INTEGRATE_FAIL", room, msg);
      await this.savePipelineState({
        lastRoom:      room,
        lastAction:    "INTEGRATE",
        lastCompleted: "SORT",
        lastFailed:    "INTEGRATE",
        resumeFrom:    "INTEGRATE",
        timestamp:     new Date().toISOString(),
      });
      throw err;
    }
  }

  /**
   * Run the full pipeline in one call.
   * lock → split → sort → integrate
   */
  public async runFullPipeline(
    room:    string,
    version: string
  ): Promise<void> {
    this.log("INFO", `Starting full pipeline for ${room} @ ${version}`);

    await this.lock(room, version);
    await this.split(room);
    await this.sort(room);
    await this.integrate(room);

    this.emit("pipeline:done", room);
    this.audit("PIPELINE_COMPLETE", room, `version=${version}`);
    this.log("SUCCESS", `Full pipeline complete: ${room}`);
  }

  /**
   * Resume pipeline from last failed phase.
   */
  public async resume(room?: string): Promise<void> {
    const state = await this.getPipelineState();

    if (!state || !state.resumeFrom) {
      throw new Error("No failed pipeline state to resume from");
    }

    const targetRoom = room ?? state.lastRoom;
    if (!targetRoom) throw new Error("No room specified for resume");

    this.log("INFO", `Resuming ${targetRoom} from ${state.resumeFrom}`);

    const phases: PipelinePhase[] = ["LOCK", "SPLIT", "SORT", "INTEGRATE"];
    const startIdx = phases.indexOf(state.resumeFrom);

    if (startIdx === -1) {
      throw new Error(`Unknown resume phase: ${state.resumeFrom}`);
    }

    for (let i = startIdx; i < phases.length; i++) {
      const phase = phases[i];
      switch (phase) {
        case "SPLIT":     await this.split(targetRoom);     break;
        case "SORT":      await this.sort(targetRoom);      break;
        case "INTEGRATE": await this.integrate(targetRoom); break;
      }
    }
  }


  // ──────────────────────────────────────────────────────────
  //  SESSION MANAGEMENT
  // ──────────────────────────────────────────────────────────

  /**
   * Hash a PIN using PBKDF2-SHA256.
   * Matches the Python implementation exactly.
   */
  private hashPin(pin: string): string {
    const salt       = Buffer.from("aizquad_sovereign_salt_v1");
    const iterations = 260_000;
    const keylen     = 32;
    const digest     = "sha256";

    return crypto
      .pbkdf2Sync(pin, salt, iterations, keylen, digest)
      .toString("hex");
  }

  /**
   * Setup PIN (first-time or reset).
   */
  public async setupPin(pin: string): Promise<void> {
    if (!pin || pin.length < 4) {
      throw new Error("PIN must be at least 4 characters");
    }

    const hash = this.hashPin(pin);
    fs.writeFileSync(this.paths.pin, hash, { encoding: "utf8", mode: 0o600 });
    this.audit("PIN_SET", "system", "PIN configured");
    this.log("INFO", "PIN configured successfully");
  }

  /**
   * Unlock the workstation with a PIN.
   */
  public async unlock(pin: string): Promise<boolean> {
    if (!fs.existsSync(this.paths.pin)) {
      throw new Error("PIN not configured. Run setupPin() first.");
    }

    if (this.pinAttempts >= this.config.maxPinAttempts) {
      const msg = `Max PIN attempts (${this.config.maxPinAttempts}) exceeded. Locked.`;
      this.audit("PIN_LOCKED", "system", msg);
      throw new Error(msg);
    }

    const storedHash   = fs.readFileSync(this.paths.pin, "utf8").trim();
    const attemptHash  = this.hashPin(pin);

    if (storedHash !== attemptHash) {
      this.pinAttempts++;
      this.audit(
        "PIN_FAIL",
        "system",
        `attempt=${this.pinAttempts}/${this.config.maxPinAttempts}`
      );
      this.log("WARN", `Wrong PIN (attempt ${this.pinAttempts})`);
      return false;
    }

    // Reset attempts on success
    this.pinAttempts = 0;

    const now     = Date.now() / 1000;
    const expires = now + (this.config.sessionTTLHours * 3600);
    const session: SessionState = {
      active:    true,
      createdAt: now,
      expiresAt: expires,
      ttlHours:  this.config.sessionTTLHours,
    };

    fs.writeFileSync(
      this.paths.session,
      JSON.stringify(session),
      { encoding: "utf8", mode: 0o600 }
    );

    this.startSessionTimer(expires - now);
    this.emit("session:unlocked");
    this.audit("SESSION_UNLOCKED", "system", `ttl=${this.config.sessionTTLHours}h`);
    this.log("SUCCESS", "Workstation unlocked");
    return true;
  }

  /**
   * Lock the workstation immediately.
   */
  public lockWorkstation(): void {
    if (fs.existsSync(this.paths.session)) {
      fs.unlinkSync(this.paths.session);
    }

    this.clearSessionTimer();
    this.emit("session:locked");
    this.audit("SESSION_LOCKED", "system", "manual lock");
    this.log("INFO", "Workstation locked");
  }

  /**
   * Check if session is currently active.
   */
  public isUnlocked(): boolean {
    if (!fs.existsSync(this.paths.session)) return false;

    try {
      const session: SessionState = JSON.parse(
        fs.readFileSync(this.paths.session, "utf8")
      );
      const now = Date.now() / 1000;

      if (!session.active || now > session.expiresAt) {
        this.lockWorkstation();
        return false;
      }
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Refresh session TTL (extend expiry).
   */
  public refreshSession(): void {
    if (!this.isUnlocked()) {
      throw new Error("No active session to refresh");
    }

    const session: SessionState = JSON.parse(
      fs.readFileSync(this.paths.session, "utf8")
    );

    const now     = Date.now() / 1000;
    const expires = now + (this.config.sessionTTLHours * 3600);
    session.expiresAt = expires;

    fs.writeFileSync(
      this.paths.session,
      JSON.stringify(session),
      { encoding: "utf8", mode: 0o600 }
    );

    this.clearSessionTimer();
    this.startSessionTimer(expires - now);
    this.emit("session:refresh");
    this.log("INFO", "Session refreshed");
  }

  /**
   * Get time remaining in current session (seconds).
   */
  public sessionTimeRemaining(): number {
    if (!fs.existsSync(this.paths.session)) return 0;

    try {
      const session: SessionState = JSON.parse(
        fs.readFileSync(this.paths.session, "utf8")
      );
      const remaining = session.expiresAt - (Date.now() / 1000);
      return Math.max(0, remaining);
    } catch {
      return 0;
    }
  }

  private startSessionTimer(ttlSeconds: number): void {
    this.clearSessionTimer();
    this.sessionTimer = setTimeout(() => {
      this.lockWorkstation();
      this.emit("session:expired");
      this.log("WARN", "Session expired — workstation locked");
    }, ttlSeconds * 1000);
  }

  private clearSessionTimer(): void {
    if (this.sessionTimer) {
      clearTimeout(this.sessionTimer);
      this.sessionTimer = null;
    }
  }


  // ──────────────────────────────────────────────────────────
  //  AI ACCESS CONTROL
  // ──────────────────────────────────────────────────────────

  /**
   * Grant AI access to a room.
   * Requires active session.
   */
  public grantAIAccess(room: string, level: AIAccessLevel): void {
    this.requireSession();

    const access = this.readAIAccess();
    access[room] = {
      level,
      grantedAt: new Date().toISOString(),
      active:    true,
    };
    this.writeAIAccess(access);

    this.emit("ai:granted", room, level);
    this.audit("AI_ACCESS_GRANTED", room, `level=${level}`);
    this.log("INFO", `AI access granted: ${room} @ ${level}`);
  }

  /**
   * Revoke AI access for a room.
   */
  public revokeAIAccess(room: string): void {
    this.requireSession();

    const access = this.readAIAccess();
    if (access[room]) {
      access[room].active = false;
      this.writeAIAccess(access);
    }

    this.emit("ai:revoked", room);
    this.audit("AI_ACCESS_REVOKED", room, "revoked by user");
    this.log("INFO", `AI access revoked: ${room}`);
  }

  /**
   * Revoke ALL AI access immediately.
   */
  public revokeAllAIAccess(): void {
    this.requireSession();

    const access = this.readAIAccess();
    for (const room of Object.keys(access)) {
      access[room].active = false;
      this.emit("ai:revoked", room);
    }
    this.writeAIAccess(access);

    this.audit("AI_ACCESS_REVOKE_ALL", "system", "all rooms revoked");
    this.log("WARN", "All AI access revoked");
  }

  /**
   * Get AI access level for a room.
   * Returns "none" if not granted or inactive.
   */
  public getAIAccessLevel(room: string): AIAccessLevel {
    const access = this.readAIAccess();
    const record = access[room];

    if (!record || !record.active) return "none";
    return record.level;
  }

  /**
   * Check if AI can access a specific room.
   */
  public canAIAccess(room: string): boolean {
    return this.getAIAccessLevel(room) !== "none";
  }

  /**
   * Get full AI access map.
   */
  public getAIAccessMap(): AIAccessMap {
    return this.readAIAccess();
  }

  private readAIAccess(): AIAccessMap {
    if (!fs.existsSync(this.paths.aiAccess)) return {};
    try {
      return JSON.parse(fs.readFileSync(this.paths.aiAccess, "utf8"));
    } catch {
      return {};
    }
  }

  private writeAIAccess(access: AIAccessMap): void {
    fs.writeFileSync(
      this.paths.aiAccess,
      JSON.stringify(access, null, 2),
      { encoding: "utf8", mode: 0o600 }
    );
  }


  // ──────────────────────────────────────────────────────────
  //  PIPELINE STATE
  // ──────────────────────────────────────────────────────────

  public async savePipelineState(state: PipelineState): Promise<void> {
    fs.writeFileSync(
      this.paths.pipeState,
      JSON.stringify(state, null, 2),
      "utf8"
    );
  }

  public async getPipelineState(): Promise<PipelineState | null> {
    if (!fs.existsSync(this.paths.pipeState)) return null;
    try {
      return JSON.parse(fs.readFileSync(this.paths.pipeState, "utf8"));
    } catch {
      return null;
    }
  }


  // ──────────────────────────────────────────────────────────
  //  MESH & LOCK READERS
  // ──────────────────────────────────────────────────────────

  /**
   * Read the mesh manifest.
   */
  public getMeshManifest(): MeshManifest | null {
    const manifestPath = path.join(this.paths.mesh, "mesh_manifest.json");
    if (!fs.existsSync(manifestPath)) return null;
    try {
      return JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    } catch {
      return null;
    }
  }

  /**
   * List all rooms in the mesh.
   */
  public listMeshRooms(): string[] {
    const manifest = this.getMeshManifest();
    return manifest?.rooms ?? [];
  }

  /**
   * Read a logic lock record for a room.
   */
  public getLogicLock(room: string): Record<string, unknown> | null {
    const lockPath = path.join(
      this.paths.integration,
      "logic_locks",
      `${room}.logic.json`
    );
    if (!fs.existsSync(lockPath)) return null;
    try {
      return JSON.parse(fs.readFileSync(lockPath, "utf8"));
    } catch {
      return null;
    }
  }

  /**
   * Verify a room's logic lock against current mesh state.
   */
  public async verifyRoom(room: string): Promise<boolean> {
    const lock = this.getLogicLock(room);
    if (!lock) {
      this.log("WARN", `No logic lock found for ${room}`);
      return false;
    }

    try {
      const result = await this.runMake("verify", { ROOM: room });
      const verified = result.exitCode === 0;

      if (verified) {
        this.audit("VERIFY_OK", room, "signature match");
        this.log("SUCCESS", `Verification passed: ${room}`);
      } else {
        this.audit("VERIFY_FAIL", room, "signature mismatch — TAMPERED");
        this.log("ERROR", `Verification FAILED: ${room} — possible tampering`);
      }

      return verified;
    } catch {
      this.audit("VERIFY_FAIL", room, "verify command failed");
      return false;
    }
  }

  /**
   * List all forge-locked rooms.
   */
  public listLockedRooms(): LockRecord[] {
    const lockedDir = path.join(this.paths.forge, "locked");
    if (!fs.existsSync(lockedDir)) return [];

    const records: LockRecord[] = [];
    for (const file of fs.readdirSync(lockedDir)) {
      if (file.endsWith(".lock.json")) {
        try {
          const data = JSON.parse(
            fs.readFileSync(path.join(lockedDir, file), "utf8")
          );
          records.push(data as LockRecord);
        } catch {
          // Skip corrupt files
        }
      }
    }
    return records;
  }


  // ──────────────────────────────────────────────────────────
  //  AUDIT LOG
  // ──────────────────────────────────────────────────────────

  /**
   * Write an audit log entry.
   * Always appends — never overwrites.
   */
  private audit(action: string, room: string, detail: string): void {
    const entry: LogEntry = {
      ts:     new Date().toISOString(),
      action,
      room,
      detail,
    };

    const line = JSON.stringify(entry) + "\n";
    fs.appendFileSync(this.paths.auditLog, line, "utf8");
    this.emit("audit:entry", entry);
  }

  /**
   * Read last N audit log entries.
   */
  public getAuditLog(limit = 50): LogEntry[] {
    if (!fs.existsSync(this.paths.auditLog)) return [];

    try {
      const lines = fs
        .readFileSync(this.paths.auditLog, "utf8")
        .trim()
        .split("\n")
        .filter(Boolean);

      return lines
        .slice(-limit)
        .map(line => JSON.parse(line) as LogEntry)
        .reverse(); // Most recent first
    } catch {
      return [];
    }
  }

  /**
   * Filter audit log by action type.
   */
  public getAuditByAction(action: string, limit = 20): LogEntry[] {
    return this.getAuditLog(200).filter(e =>
      e.action.includes(action)
    ).slice(0, limit);
  }

  /**
   * Filter audit log by room.
   */
  public getAuditByRoom(room: string, limit = 20): LogEntry[] {
    return this.getAuditLog(200).filter(e =>
      e.room === room
    ).slice(0, limit);
  }


  // ──────────────────────────────────────────────────────────
  //  GUARDS
  // ──────────────────────────────────────────────────────────

  /**
   * Throw if no active session.
   * Called before any sensitive operation.
   */
  private requireSession(): void {
    if (!this.isUnlocked()) {
      const err = new Error("No active session. Unlock workstation first.");
      this.emit("ai:denied", "system", err.message);
      throw err;
    }
  }


  // ──────────────────────────────────────────────────────────
  //  LOGGING
  // ──────────────────────────────────────────────────────────

  private log(level: LogLevel, message: string, detail?: string): void {
    const levels: LogLevel[] = ["DEBUG", "INFO", "WARN", "ERROR", "SUCCESS"];
    const configIdx   = levels.indexOf(this.config.logLevel);
    const messageIdx  = levels.indexOf(level);

    if (messageIdx < configIdx && level !== "ERROR") return;

    const colors: Record<LogLevel, string> = {
      DEBUG:   "\x1b[90m",
      INFO:    "\x1b[96m",
      WARN:    "\x1b[93m",
      ERROR:   "\x1b[91m",
      SUCCESS: "\x1b[92m",
    };

    const reset  = "\x1b[0m";
    const color  = colors[level] ?? "";
    const ts     = new Date().toISOString();
    const detail_ = detail ? ` | ${detail}` : "";

    console.log(
      `${color}[${level}]${reset} ${ts} — ${message}${detail_}`
    );
  }


  // ──────────────────────────────────────────────────────────
  //  CLEANUP
  // ──────────────────────────────────────────────────────────

  /**
   * Clean up timers and processes.
   * Call on process exit.
   */
  public destroy(): void {
    this.clearSessionTimer();
    this.kill();
    this.removeAllListeners();
    this.log("INFO", "TerminalBridge destroyed");
  }
}
