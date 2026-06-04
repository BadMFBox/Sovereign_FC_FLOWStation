// ═══════════════════════════════════════════════════════════════
//  tests/ts/bridge.test.ts
//  TerminalBridge unit tests — Jest
// ═══════════════════════════════════════════════════════════════

import * as fs   from "fs";
import * as path from "path";
import * as os   from "os";
import { TerminalBridge } from "../../TerminalBridge";

describe("TerminalBridge", () => {

  let bridge:    TerminalBridge;
  let workspace: string;

  beforeEach(() => {
    workspace = fs.mkdtempSync(path.join(os.tmpdir(), "aizquad-test-"));
    bridge    = new TerminalBridge({
      workspaceRoot:   workspace,
      sessionTTLHours: 0.01, // 36 seconds for fast tests
      maxPinAttempts:  3,
    });
  });

  afterEach(() => {
    bridge.destroy();
    fs.rmSync(workspace, { recursive: true, force: true });
  });

  // ── SESSION ─────────────────────────────────────────────────

  describe("Session Management", () => {

    test("setup and unlock with correct PIN", async () => {
      await bridge.setupPin("1234");
      const ok = await bridge.unlock("1234");
      expect(ok).toBe(true);
      expect(bridge.isUnlocked()).toBe(true);
    });

    test("wrong PIN returns false", async () => {
      await bridge.setupPin("1234");
      const ok = await bridge.unlock("9999");
      expect(ok).toBe(false);
      expect(bridge.isUnlocked()).toBe(false);
    });

    test("lock clears session", async () => {
      await bridge.setupPin("1234");
      await bridge.unlock("1234");
      expect(bridge.isUnlocked()).toBe(true);
      bridge.lockWorkstation();
      expect(bridge.isUnlocked()).toBe(false);
    });

    test("session has positive time remaining", async () => {
      await bridge.setupPin("1234");
      await bridge.unlock("1234");
      expect(bridge.sessionTimeRemaining()).toBeGreaterThan(0);
    });

    test("locked session has zero time remaining", () => {
      expect(bridge.sessionTimeRemaining()).toBe(0);
    });

    test("max PIN attempts locks out", async () => {
      await bridge.setupPin("1234");
      await bridge.unlock("wrong");
      await bridge.unlock("wrong");
      await bridge.unlock("wrong");
      await expect(bridge.unlock("wrong")).rejects.toThrow(/exceeded/);
    });

    test("PIN is never stored in plaintext", async () => {
      await bridge.setupPin("mysecretpin");
      const pinPath = path.join(workspace, "shared", ".pin");
      const content = fs.readFileSync(pinPath, "utf8");
      expect(content).not.toContain("mysecretpin");
      expect(content.length).toBe(64); // SHA-256 hex
    });
  });

  // ── AI ACCESS ───────────────────────────────────────────────

  describe("AI Access Control", () => {

    beforeEach(async () => {
      await bridge.setupPin("1234");
      await bridge.unlock("1234");
    });

    test("grant surface access", () => {
      bridge.grantAIAccess("room-test", "surface");
      expect(bridge.getAIAccessLevel("room-test")).toBe("surface");
      expect(bridge.canAIAccess("room-test")).toBe(true);
    });

    test("grant read access", () => {
      bridge.grantAIAccess("room-test", "read");
      expect(bridge.getAIAccessLevel("room-test")).toBe("read");
    });

    test("revoke access sets level to none", () => {
      bridge.grantAIAccess("room-test", "surface");
      bridge.revokeAIAccess("room-test");
      expect(bridge.getAIAccessLevel("room-test")).toBe("none");
      expect(bridge.canAIAccess("room-test")).toBe(false);
    });

    test("revoke all clears all rooms", () => {
      bridge.grantAIAccess("room-1", "surface");
      bridge.grantAIAccess("room-2", "read");
      bridge.grantAIAccess("room-3", "surface");
      bridge.revokeAllAIAccess();
      expect(bridge.canAIAccess("room-1")).toBe(false);
      expect(bridge.canAIAccess("room-2")).toBe(false);
      expect(bridge.canAIAccess("room-3")).toBe(false);
    });

    test("no access for unknown room", () => {
      expect(bridge.getAIAccessLevel("nonexistent")).toBe("none");
    });

    test("grant without session throws", async () => {
      bridge.lockWorkstation();
      expect(() => bridge.grantAIAccess("room-test", "surface"))
        .toThrow(/session/i);
    });
  });

  // ── AUDIT LOG ───────────────────────────────────────────────

  describe("Audit Log", () => {

    beforeEach(async () => {
      await bridge.setupPin("1234");
      await bridge.unlock("1234");
    });

    test("audit log created on unlock", () => {
      const logPath = path.join(workspace, "shared", "audit.log");
      expect(fs.existsSync(logPath)).toBe(true);
    });

    test("audit entries are valid JSON lines", () => {
      bridge.grantAIAccess("room-test", "surface");
      const entries = bridge.getAuditLog(10);
      expect(entries.length).toBeGreaterThan(0);
      for (const entry of entries) {
        expect(entry).toHaveProperty("ts");
        expect(entry).toHaveProperty("action");
        expect(entry).toHaveProperty("room");
      }
    });

    test("getAuditByAction filters correctly", () => {
      bridge.grantAIAccess("room-a", "surface");
      bridge.revokeAIAccess("room-a");
      const grants = bridge.getAuditByAction("GRANTED");
      expect(grants.every(e => e.action.includes("GRANTED"))).toBe(true);
    });

    test("getAuditByRoom filters correctly", () => {lll
      bridge.grantAIAccess("room-a", "surface");
      bridge.grantAIAccess("room-b", "read");
      const entries = bridge.getAuditByRoom("room-a");
      expect(entries.every(e => e.room === "room-a")).toBe(true);
    });

    test("audit log is append only", () => {
      bridge.grantAIAccess("room-test", "surface");
      bridge.revokeAIAccess("room-test");
      bridge.grantAIAccess("room-test", "read");

      const logPath = path.join(workspace, "shared", "audit.log");
      const lines   = fs
        .readFileSync(logPath, "utf8")
        .trim()
        .split("\n")
        .filter(Boolean);

      // All lines must be valid JSON
      for (const line of lines) {
        expect(() => JSON.parse(line)).not.toThrow();
      }

      // Must have multiple entries — never overwritten
      expect(lines.length).toBeGreaterThan(2);
    });

    test("audit entries have ISO 8601 timestamps", () => {
      bridge.grantAIAccess("room-test", "surface");
      const entries = bridge.getAuditLog(5);
      for (const entry of entries) {
        expect(() => new Date(entry.ts)).not.toThrow();
        expect(entry.ts).toMatch(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
      }
    });

    test("audit emits entry event", done => {
      bridge.on("audit:entry", entry => {
        expect(entry.action).toBe("AI_ACCESS_GRANTED");
        expect(entry.room).toBe("room-test");
        done();
      });
      bridge.grantAIAccess("room-test", "surface");
    });
  });

  // ── PIPELINE STATE ──────────────────────────────────────────

  describe("Pipeline State", () => {

    test("save and retrieve pipeline state", async () => {
      await bridge.savePipelineState({
        lastRoom:      "room-test",
        lastAction:    "LOCK",
        lastCompleted: "LOCK",
        lastFailed:    null,
        resumeFrom:    null,
        timestamp:     new Date().toISOString(),
      });

      const state = await bridge.getPipelineState();
      expect(state).not.toBeNull();
      expect(state?.lastRoom).toBe("room-test");
      expect(state?.lastAction).toBe("LOCK");
      expect(state?.lastCompleted).toBe("LOCK");
    });

    test("failed state records resume point", async () => {
      await bridge.savePipelineState({
        lastRoom:      "room-test",
        lastAction:    "SORT",
        lastCompleted: "SPLIT",
        lastFailed:    "SORT",
        resumeFrom:    "SORT",
        timestamp:     new Date().toISOString(),
      });

      const state = await bridge.getPipelineState();
      expect(state?.lastFailed).toBe("SORT");
      expect(state?.resumeFrom).toBe("SORT");
      expect(state?.lastCompleted).toBe("SPLIT");
    });

    test("returns null when no state file exists", async () => {
      const state = await bridge.getPipelineState();
      expect(state).toBeNull();
    });

    test("state is valid JSON on disk", async () => {
      await bridge.savePipelineState({
        lastRoom:      "room-test",
        lastAction:    "INTEGRATE",
        lastCompleted: "INTEGRATE",
        lastFailed:    null,
        resumeFrom:    null,
        timestamp:     new Date().toISOString(),
      });

      const statePath = path.join(workspace, "shared", "pipeline_state.json");
      const raw       = fs.readFileSync(statePath, "utf8");
      expect(() => JSON.parse(raw)).not.toThrow();
    });
  });

  // ── MESH READERS ────────────────────────────────────────────

  describe("Mesh Readers", () => {

    test("getMeshManifest returns null when missing", () => {
      expect(bridge.getMeshManifest()).toBeNull();
    });

    test("getMeshManifest reads correctly", () => {
      const meshDir  = path.join(workspace, "integration", "output", "mesh");
      fs.mkdirSync(meshDir, { recursive: true });

      const manifest = {
        mesh_version: "1.0",
        rooms:        ["room-1", "room-2"],
        room_count:   2,
        status:       "wired",
        wired_at:     new Date().toISOString(),
      };

      fs.writeFileSync(
        path.join(meshDir, "mesh_manifest.json"),
        JSON.stringify(manifest),
        "utf8"
      );

      const loaded = bridge.getMeshManifest();
      expect(loaded).not.toBeNull();
      expect(loaded?.rooms).toEqual(["room-1", "room-2"]);
      expect(loaded?.status).toBe("wired");
    });

    test("listMeshRooms returns empty array when no manifest", () => {
      expect(bridge.listMeshRooms()).toEqual([]);
    });

    test("listMeshRooms returns all rooms from manifest", () => {
      const meshDir = path.join(workspace, "integration", "output", "mesh");
      fs.mkdirSync(meshDir, { recursive: true });

      fs.writeFileSync(
        path.join(meshDir, "mesh_manifest.json"),
        JSON.stringify({
          mesh_version: "1.0",
          rooms:        ["room-a", "room-b", "room-c"],
          room_count:   3,
          status:       "wired",
          wired_at:     new Date().toISOString(),
        }),
        "utf8"
      );

      const rooms = bridge.listMeshRooms();
      expect(rooms).toHaveLength(3);
      expect(rooms).toContain("room-a");
      expect(rooms).toContain("room-b");
      expect(rooms).toContain("room-c");
    });

    test("getLogicLock returns null when missing", () => {
      expect(bridge.getLogicLock("nonexistent-room")).toBeNull();
    });

    test("getLogicLock reads correctly", () => {
      const lockDir = path.join(
        workspace,
        "integration",
        "logic_locks"
      );
      fs.mkdirSync(lockDir, { recursive: true });

      const lock = {
        room:      "room-test",
        signature: "a".repeat(64),
        status:    "SEALED",
        sealed_at: new Date().toISOString(),
      };

      fs.writeFileSync(
        path.join(lockDir, "room-test.logic.json"),
        JSON.stringify(lock),
        "utf8"
      );

      const loaded = bridge.getLogicLock("room-test");
      expect(loaded).not.toBeNull();
      expect(loaded?.status).toBe("SEALED");
      expect((loaded?.signature as string).length).toBe(64);
    });

    test("listLockedRooms returns empty when no lock files", () => {
      expect(bridge.listLockedRooms()).toEqual([]);
    });

    test("listLockedRooms reads all lock records", () => {
      const lockedDir = path.join(workspace, "forge", "locked");
      fs.mkdirSync(lockedDir, { recursive: true });

      const rooms = ["room-1", "room-2", "room-3"];
      for (const room of rooms) {
        fs.writeFileSync(
          path.join(lockedDir, `${room}-v1.lock.json`),
          JSON.stringify({
            room,
            version:   "v1",
            locked_at: new Date().toISOString(),
            locked_by: "test",
            signature: "b".repeat(64),
            files:     5,
            status:    "LOCKED",
          }),
          "utf8"
        );
      }

      const records = bridge.listLockedRooms();
      expect(records).toHaveLength(3);
      expect(records.map(r => r.room)).toContain("room-1");
      expect(records.map(r => r.room)).toContain("room-2");
      expect(records.map(r => r.room)).toContain("room-3");
    });
  });

  // ── EVENTS ──────────────────────────────────────────────────

  describe("Event Emitter", () => {

    beforeEach(async () => {
      await bridge.setupPin("1234");
      await bridge.unlock("1234");
    });

    test("emits session:unlocked on unlock", done => {
      bridge.lockWorkstation();

      const fresh = new TerminalBridge({
        workspaceRoot: workspace,
      });

      fresh.on("session:unlocked", () => {
        fresh.destroy();
        done();
      });

      // Re-use existing PIN file
      fresh.unlock("1234");
    });

    test("emits session:locked on lockWorkstation", done => {
      bridge.on("session:locked", () => done());
      bridge.lockWorkstation();
    });

    test("emits ai:granted on grantAIAccess", done => {
      bridge.on("ai:granted", (room, level) => {
        expect(room).toBe("room-events");
        expect(level).toBe("surface");
        done();
      });
      bridge.grantAIAccess("room-events", "surface");
    });

    test("emits ai:revoked on revokeAIAccess", done => {
      bridge.grantAIAccess("room-events", "surface");
      bridge.on("ai:revoked", room => {
        expect(room).toBe("room-events");
        done();
      });
      bridge.revokeAIAccess("room-events");
    });

    test("emits ai:denied when no session", done => {
      bridge.lockWorkstation();
      bridge.on("ai:denied", (room, reason) => {
        expect(reason).toMatch(/session/i);
        done();
      });
      try {
        bridge.grantAIAccess("room-test", "surface");
      } catch {
        // Expected — denial emits before throw
      }
    });
  });

  // ── EXEC ENGINE ─────────────────────────────────────────────

  describe("Command Execution", () => {

    test("exec runs echo command successfully", async () => {
      const result = await bridge.exec("echo", ["hello sovereign"]);
      expect(result.status).toBe("SUCCESS");
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toContain("hello sovereign");
    });

    test("exec captures exit code on failure", async () => {
      await expect(
        bridge.exec("false", [])
      ).rejects.toThrow();
    });

    test("exec records duration", async () => {
      const result = await bridge.exec("echo", ["timing"]);
      expect(result.duration).toBeGreaterThanOrEqual(0);
    });

    test("exec records timestamp", async () => {
      const result = await bridge.exec("echo", ["ts"]);
      expect(() => new Date(result.timestamp)).not.toThrow();
    });

    test("emits command:start event", done => {
      bridge.on("command:start", cmd => {
        expect(cmd).toContain("echo");
        done();
      });
      bridge.exec("echo", ["event-test"]).catch(() => {});
    });

    test("emits command:stdout per line", done => {
      const lines: string[] = [];
      bridge.on("command:stdout", line => lines.push(line));
      bridge.exec("echo", ["line1"]).then(() => {
        expect(lines).toContain("line1");
        done();
      });
    });

    test("emits command:done on completion", done => {
      bridge.on("command:done", result => {
        expect(result.status).toBe("SUCCESS");
        done();
      });
      bridge.exec("echo", ["done-test"]);
    });

    test("timeout kills process and rejects", async () => {
      await expect(
        bridge.exec("sleep", ["60"], { timeout: 100 })
      ).rejects.toThrow(/timed out/i);
    });
  });

  // ── DIRECTORY SETUP ─────────────────────────────────────────

  describe("Directory Initialization", () => {

    test("creates shared directory", () => {
      expect(fs.existsSync(path.join(workspace, "shared"))).toBe(true);
    });

    test("creates forge directories", () => {
      expect(fs.existsSync(path.join(workspace, "forge", "active"))).toBe(true);
      expect(fs.existsSync(path.join(workspace, "forge", "locked"))).toBe(true);
      expect(fs.existsSync(path.join(workspace, "forge", "versions"))).toBe(true);
    });

    test("creates splitter output directory", () => {
      expect(
        fs.existsSync(path.join(workspace, "splitter", "output"))
      ).toBe(true);
    });

    test("creates sorter directories", () => {
      expect(
        fs.existsSync(path.join(workspace, "sorter", "input"))
      ).toBe(true);
      expect(
        fs.existsSync(path.join(workspace, "sorter", "output"))
      ).toBe(true);
    });

    test("creates integration directories", () => {
      expect(
        fs.existsSync(path.join(workspace, "integration", "merge"))
      ).toBe(true);
      expect(
        fs.existsSync(path.join(workspace, "integration", "logic_locks"))
      ).toBe(true);
    });

    test("creates mesh output directory", () => {
      expect(
        fs.existsSync(
          path.join(workspace, "integration", "output", "mesh")
        )
      ).toBe(true);
    });
  });

  // ── CLEANUP ─────────────────────────────────────────────────

  describe("Cleanup", () => {

    test("destroy removes all listeners", () => {
      bridge.on("session:locked", () => {});
      bridge.on("ai:granted",     () => {});
      bridge.destroy();
      expect(bridge.listenerCount("session:locked")).toBe(0);
      expect(bridge.listenerCount("ai:granted")).toBe(0);
    });

    test("isUnlocked returns false after destroy", async () => {
      await bridge.setupPin("1234");
      await bridge.unlock("1234");
      bridge.destroy();
      expect(bridge.isUnlocked()).toBe(false);
    });
  });
});
      