// ═══════════════════════════════════════════════════════════════
//  examples/bridge_usage.ts
//  Usage examples — how to wire this into any UI
// ═══════════════════════════════════════════════════════════════

import { TerminalBridge } from "./TerminalBridge";
import { getBridge }      from "./TerminalBridgeFactory";

async function main() {

  // ── 1. Create bridge ────────────────────────────────────────
  const bridge = getBridge("/path/to/AiZQuad_Lab", {
    sessionTTLHours: 4,
    maxPinAttempts:  3,
    logLevel:        "INFO",
    commandTimeout:  300_000,
  });

  // ── 2. Wire up event listeners ──────────────────────────────
  bridge.on("command:stdout",    line  => process.stdout.write(`  ${line}\n`));
  bridge.on("command:stderr",    line  => process.stderr.write(`  ⚠ ${line}\n`));
  bridge.on("pipeline:phase",   (p, r) => console.log(`\n▶ Phase: ${p} — ${r}`));
  bridge.on("pipeline:success", (p, r) => console.log(`✅ ${p} complete: ${r}`));
  bridge.on("pipeline:failed",  (p, r, e) => console.error(`❌ ${p} failed: ${r}\n${e}`));
  bridge.on("pipeline:done",     r     => console.log(`\n🔥 Pipeline done: ${r}`));
  bridge.on("session:unlocked",  ()    => console.log("🔓 Session active"));
  bridge.on("session:locked",    ()    => console.log("🔒 Workstation locked"));
  bridge.on("session:expired",   ()    => console.log("⏰ Session expired"));
  bridge.on("ai:granted",       (r, l) => console.log(`🤖 AI access: ${r} @ ${l}`));
  bridge.on("ai:revoked",        r     => console.log(`🚫 AI revoked: ${r}`));
  bridge.on("audit:entry",       e     => { /* forward to UI */ });
  bridge.on("error",             err   => console.error("Bridge error:", err));

  // ── 3. Setup PIN (first time only) ──────────────────────────
  await bridge.setupPin("your-secure-pin");

  // ── 4. Unlock ───────────────────────────────────────────────
  const ok = await bridge.unlock("your-secure-pin");
  if (!ok) {
    console.error("Wrong PIN");
    process.exit(1);
  }

  // ── 5. Run full pipeline ─────────────────────────────────────
  await bridge.runFullPipeline("room-payments", "v1");

  // ── 6. Grant AI surface access ───────────────────────────────
  bridge.grantAIAccess("room-payments", "surface");

  // ── 7. Check access ──────────────────────────────────────────
  console.log("AI level:", bridge.getAIAccessLevel("room-payments"));
  console.log("Can access:", bridge.canAIAccess("room-payments"));

  // ── 8. Verify integrity ──────────────────────────────────────
  const verified = await bridge.verifyRoom("room-payments");
  console.log("Verified:", verified);

  // ── 9. Read audit log ────────────────────────────────────────
  const log = bridge.getAuditLog(10);
  console.log("Last 10 entries:", log);

  // ── 10. Mesh info ────────────────────────────────────────────
  const manifest = bridge.getMeshManifest();
  console.log("Mesh rooms:", manifest?.rooms);

  // ── 11. Revoke + lock ────────────────────────────────────────
  bridge.revokeAIAccess("room-payments");
  bridge.lockWorkstation();

  // ── 12. Cleanup ──────────────────────────────────────────────
  bridge.destroy();
}

main().catch(console.error);

// ── Graceful shutdown ────────────────────────────────────────
process.on("SIGINT",  () => { bridge.destroy(); process.exit(0); });
process.on("SIGTERM", () => { bridge.destroy(); process.exit(0); });
