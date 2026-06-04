// ═══════════════════════════════════════════════════════════════
//  FluidDialog.ts
//  Plan-based dialog system for FlowStation
//  Real logic evolves through conversation, not commands
//
//  AiZQuad FlowStation Lab
//  Founder: Juan Jaime Rivera Zamorano
// ═══════════════════════════════════════════════════════════════

import * as readline from "readline";
import * as fs       from "fs";
import * as path     from "path";
import { EventEmitter } from "events";

import { TerminalBridge }         from "./TerminalBridge";
import { FluidScanner, FluidScan, FluidFile } from "./FluidScanner";
import { FluidDisplay }           from "./FluidDisplay";

// ───────────────────────────────────────────────────────────────
//  DIALOG TYPES
// ───────────────────────────────────────────────────────────────

export type DialogStep =
  | "WELCOME"
  | "SCAN"
  | "REVIEW"
  | "QUESTION"
  | "PLAN"
  | "APPROVE"
  | "EXECUTE"
  | "VERIFY"
  | "COMPLETE"
  | "PAUSED";

export type UserIntent =
  | "confirm"    // yes, looks right
  | "rename"     // I want to call it something else
  | "skip"       // not now
  | "question"   // I want to ask about this
  | "reorder"    // change the plan order
  | "remove"     // take this out of the plan
  | "add"        // add something to the plan
  | "approve"    // approve the full plan
  | "pause"      // stop for now, save state
  | "abort"      // cancel everything
  | "back"       // go back one step
  | "help";      // show what I can do here

export interface DialogAction {
  type:        string;      // lock | split | sort | integrate
  room:        string;
  version?:    string;
  label:       string;      // human readable
  reason:      string;      // why this action is suggested
  confirmed:   boolean;     // user approved this specific action
  order:       number;      // position in plan
}

export interface DialogPlan {
  room:        string;
  version:     string;
  actions:     DialogAction[];
  createdAt:   string;
  approvedAt:  string | null;
  notes:       string[];    // user notes added during dialog
  userOwns:    true;
}

export interface DialogContext {
  step:        DialogStep;
  room:        string;
  version:     string;
  scan:        FluidScan | null;
  plan:        DialogPlan | null;
  history:     DialogMessage[];  // full conversation history
  currentFile: FluidFile | null; // file being reviewed
  fileIndex:   number;           // where we are in review
  savedAt:     string | null;    // last save point
}

export interface DialogMessage {
  from:      "system" | "user" | "fluid";
  text:      string;
  step:      DialogStep;
  timestamp: string;
  intent?:   UserIntent;
}


// ───────────────────────────────────────────────────────────────
//  FLUID DIALOG CLASS
// ───────────────────────────────────────────────────────────────

export class FluidDialog extends EventEmitter {

  private ctx:     DialogContext;
  private rl:      readline.Interface;
  private scanner: FluidScanner;

  // Colors
  private C = {
    cyan:    "\x1b[96m",
    green:   "\x1b[92m",
    yellow:  "\x1b[93m",
    red:     "\x1b[91m",
    dim:     "\x1b[2m",
    bold:    "\x1b[1m",
    magenta: "\x1b[95m",
    blue:    "\x1b[94m",
    reset:   "\x1b[0m",
  };

  constructor(
    private bridge:  TerminalBridge,
    private options: {
      room:    string;
      version: string;
      resume?: boolean;   // resume from saved dialog state
    }
  ) {
    super();

    this.scanner = new FluidScanner(bridge);

    this.ctx = {
      step:        "WELCOME",
      room:        options.room,
      version:     options.version,
      scan:        null,
      plan:        null,
      history:     [],
      currentFile: null,
      fileIndex:   0,
      savedAt:     null,
    };

    this.rl = readline.createInterface({
      input:  process.stdin,
      output: process.stdout,
    });
  }


  // ──────────────────────────────────────────────────────────
  //  ENTRY POINT
  // ──────────────────────────────────────────────────────────

  async start(): Promise<DialogPlan | null> {
    // Resume from saved state if available
    if (this.options.resume) {
      const saved = this.loadDialogState();
      if (saved) {
        this.ctx = saved;
        this.say("fluid",
          `Resuming dialog for ${this.ctx.room} @ step: ${this.ctx.step}`
        );
      }
    }

    // Run the dialog loop
    await this.runStep(this.ctx.step);

    this.rl.close();
    return this.ctx.plan;
  }


  // ──────────────────────────────────────────────────────────
  //  STEP ROUTER
  // ──────────────────────────────────────────────────────────

  private async runStep(step: DialogStep): Promise<void> {
    this.ctx.step = step;
    this.saveDialogState(); // auto-save at every step

    switch (step) {
      case "WELCOME":  await this.stepWelcome();  break;
      case "SCAN":     await this.stepScan();     break;
      case "REVIEW":   await this.stepReview();   break;
      case "QUESTION": await this.stepQuestion(); break;
      case "PLAN":     await this.stepPlan();     break;
      case "APPROVE":  await this.stepApprove();  break;
      case "EXECUTE":  await this.stepExecute();  break;
      case "VERIFY":   await this.stepVerify();   break;
      case "COMPLETE": await this.stepComplete(); break;
      case "PAUSED":   this.stepPaused();         break;
    }
  }


  // ──────────────────────────────────────────────────────────
  //  STEP 1 — WELCOME
  // ──────────────────────────────────────────────────────────

  private async stepWelcome(): Promise<void> {
    this.clear();
    this.header("FlowStation Fluid Dialog");

    this.say("fluid", [
      `Hey. Let's work on ${this.C.bold}${this.ctx.room}${this.C.reset}.`,
      ``,
      `This isn't a one-shot command.`,
      `We're going to go through it together, step by step.`,
      `You see everything. You decide everything.`,
      `I'm just here to make it flow better.`,
      ``,
      `Type ${this.C.bold}help${this.C.reset} at any point to see your options.`,
      `Type ${this.C.bold}pause${this.C.reset} to save and come back later.`,
      `Type ${this.C.bold}abort${this.C.reset} to cancel everything.`,
    ]);

    const input = await this.ask(
      "Ready to scan the room? (yes / pause / abort)"
    );

    const intent = this.parseIntent(input);

    switch (intent) {
      case "confirm": await this.runStep("SCAN"); break;
      case "pause":   await this.runStep("PAUSED"); break;
      case "abort":   this.abort(); break;
      case "help":
        this.showHelp("WELCOME");
        await this.runStep("WELCOME");
        break;
      default:
        // If they type anything affirmative, proceed
        if (this.isYes(input)) {
          await this.runStep("SCAN");
        } else {
          this.say("fluid", "Just type yes when you're ready.");
          await this.runStep("WELCOME");
        }
    }
  }


  // ──────────────────────────────────────────────────────────
  //  STEP 2 — SCAN
  // ──────────────────────────────────────────────────────────

  private async stepScan(): Promise<void> {
    this.say("fluid", `Scanning ${this.ctx.room}...`);

    const roomPath = path.join(
      this.bridge.getConfig().workspaceRoot,
      "forge",
      "active",
      this.ctx.room
    );

    if (!fs.existsSync(roomPath)) {
      this.say("fluid", [
        `${this.C.red}Room not found:${this.C.reset} ${roomPath}`,
        ``,
        `Make sure the room exists in forge/active/`,
        `before starting the dialog.`,
      ]);
      this.abort();
      return;
    }

    // Run the scan
    this.ctx.scan = this.scanner.scan(roomPath, this.ctx.room);

    this.say("fluid", [
      ``,
      `Scan complete.`,
      `Found ${this.C.bold}${this.ctx.scan.files.length} file(s)${this.C.reset}.`,
      ``,
      this.ctx.scan.summary,
      ``,
      `I'll show you each file and what I think it is.`,
      `You tell me if I'm right, rename it, or skip it.`,
      `Nothing is set until you say so.`,
    ]);

    const input = await this.ask("Ready to review? (yes / pause / abort)");
    const intent = this.parseIntent(input);

    switch (intent) {
      case "confirm":
      case "help":
        this.ctx.fileIndex = 0;
        await this.runStep("REVIEW");
        break;
      case "pause": await this.runStep("PAUSED"); break;
      case "abort": this.abort(); break;
      default:
        if (this.isYes(input)) {
          this.ctx.fileIndex = 0;
          await this.runStep("REVIEW");
        } else {
          await this.runStep("REVIEW");
        }
    }
  }


  // ──────────────────────────────────────────────────────────
  //  STEP 3 — REVIEW (file by file dialog)
  // ──────────────────────────────────────────────────────────

  private async stepReview(): Promise<void> {
    const files = this.ctx.scan?.files ?? [];

    // All files reviewed
    if (this.ctx.fileIndex >= files.length) {
      this.say("fluid", [
        ``,
        `Review complete.`,
        `Let me put together a plan based on what we found.`,
      ]);
      await this.runStep("PLAN");
      return;
    }

    const file    = files[this.ctx.fileIndex];
    this.ctx.currentFile = file;

    const total   = files.length;
    const current = this.ctx.fileIndex + 1;

    this.clear();
    this.header(`Review — File ${current} of ${total}`);

    // Show file info
    this.box([
      `${this.C.bold}File:${this.C.reset}     ${file.raw}`,
      `${this.C.bold}Label:${this.C.reset}    ${file.tag.name}`,
      `${this.C.bold}Type:${this.C.reset}     ${file.tag.type.toUpperCase()}`,
      `${this.C.bold}Flow:${this.C.reset}     ${file.flow}`,
      `${this.C.bold}Confidence:${this.C.reset} ${Math.round(file.tag.confidence * 100)}%`,
    ]);

    // Show observations
    if (file.notes && file.notes.length > 0) {
      console.log(`\n${this.C.dim}  Observations:${this.C.reset}`);
      for (const note of file.notes) {
        console.log(`${this.C.dim}  💡 ${note}${this.C.reset}`);
      }
    }

    // Show progress bar
    this.progressBar(current, total);

    console.log("");
    console.log(
      `${this.C.dim}  Options: ${this.C.reset}` +
      `${this.C.bold}yes${this.C.reset} · ` +
      `${this.C.bold}rename <name>${this.C.reset} · ` +
      `${this.C.bold}skip${this.C.reset} · ` +
      `${this.C.bold}?${this.C.reset} ask · ` +
      `${this.C.bold}back${this.C.reset} · ` +
      `${this.C.bold}pause${this.C.reset}`
    );

    const input = await this.ask(`What do you think?`);
    await this.handleReviewInput(input, file);
  }

  private async handleReviewInput(
    input: string,
    file:  FluidFile
  ): Promise<void> {

    const lower  = input.trim().toLowerCase();
    const intent = this.parseIntent(input);

    // YES — confirm the tag
    if (intent === "confirm" || this.isYes(input)) {
      file.tag.confirmed = true;
      this.say("fluid", `✅ Got it — ${file.tag.name}`);
      this.ctx.fileIndex++;
      await this.runStep("REVIEW");
      return;
    }

    // RENAME — user wants a different label
    if (intent === "rename" || lower.startsWith("rename ")) {
      const newName = input.replace(/^rename\s+/i, "").trim();
      if (newName.length > 0) {
        const oldName    = file.tag.name;
        file.tag.name    = `[${file.tag.type.toUpperCase()}] ${newName}`;
        file.tag.confirmed = true;
        this.say("fluid", `✏️  Renamed: ${oldName} → ${file.tag.name}`);
      } else {
        const name = await this.ask("What would you like to call it?");
        file.tag.name    = `[${file.tag.type.toUpperCase()}] ${name}`;
        file.tag.confirmed = true;
        this.say("fluid", `✏️  Renamed to: ${file.tag.name}`);
      }
      this.ctx.fileIndex++;
      await this.runStep("REVIEW");
      return;
    }

    // SKIP — not now
    if (intent === "skip") {
      file.tag.confirmed = false;
      this.say("fluid", `⏭  Skipped — moving on`);
      this.ctx.fileIndex++;
      await this.runStep("REVIEW");
      return;
    }

    // QUESTION — user wants to ask about this file
    if (intent === "question" || input.startsWith("?")) {
      const question = input.replace(/^\?\s*/, "").trim();
      await this.handleQuestion(question, file);
      // Come back to same file after question
      await this.runStep("REVIEW");
      return;
    }

    // BACK — go to previous file
    if (intent === "back") {
      if (this.ctx.fileIndex > 0) {
        this.ctx.fileIndex--;
        this.say("fluid", "↩  Going back one file");
      } else {
        this.say("fluid", "Already at the first file");
      }
      await this.runStep("REVIEW");
      return;
    }

    // PAUSE
    if (intent === "pause") {
      await this.runStep("PAUSED");
      return;
    }

    // ABORT
    if (intent === "abort") {
      this.abort();
      return;
    }

    // HELP
    if (intent === "help") {
      this.showHelp("REVIEW");
      await this.runStep("REVIEW");
      return;
    }

    // CHANGE TYPE — user says what type it is
    if (lower.startsWith("type ")) {
      const newType = lower.replace("type ", "").trim();
      const valid   = ["auth", "core", "config", "model", "api", "util", "mesh", "validation"];
      if (valid.includes(newType)) {
        file.tag.type      = newType;
        file.tag.name      = `[${newType.toUpperCase()}] ${file.raw.replace(/\.(py|ts|js)$/, "")}`;
        file.tag.confirmed = true;
        this.say("fluid", `🏷  Type changed to: ${newType.toUpperCase()}`);
        this.ctx.fileIndex++;
        await this.runStep("REVIEW");
      } else {
        this.say("fluid", `Unknown type. Valid: ${valid.join(", ")}`);
        await this.runStep("REVIEW");
      }
      return;
    }

    // Unrecognized — guide them
    this.say("fluid", [
      `Didn't catch that.`,
      `Try: yes / rename <name> / skip / ? <question> / back / pause`,
    ]);
    await this.runStep("REVIEW");
  }


  // ──────────────────────────────────────────────────────────
  //  STEP 4 — QUESTION (inline Q&A during review)
  // ──────────────────────────────────────────────────────────

  private async stepQuestion(): Promise<void> {
    const input    = await this.ask("What's your question?");
    await this.handleQuestion(input, this.ctx.currentFile);
  }

  private async handleQuestion(
    question: string,
    file:     FluidFile | null
  ): Promise<void> {

    // Answer based on what we know locally
    // No API calls unless user explicitly wants AI
    const answers = this.localAnswer(question, file);

    this.say("fluid", answers);

    const followUp = await this.ask(
      "Does that help? (yes / ask more / skip)"
    );

    if (this.isYes(followUp)) {
      return; // Back to wherever we came from
    }

    if (followUp.toLowerCase().startsWith("ask ") ||
        followUp.trim() === "ask more") {
      const next = followUp.replace(/^ask\s*/i, "").trim();
      await this.handleQuestion(next || "", file);
    }
  }

  /**
   * Answer questions locally without API calls.
   * Based on context we already have.
   */
  private localAnswer(
    question: string,
    file:     FluidFile | null
  ): string[] {

    const q = question.toLowerCase();

    if (!question) {
      return ["What would you like to know? Just ask."];
    }

    // Questions about a specific file
    if (file) {
      if (q.includes("why") && (q.includes("auth") || q.includes("type"))) {
        return [
          `I labeled ${file.raw} as ${file.tag.type.toUpperCase()} because`,
          `I found matching patterns in the filename and content.`,
          `Confidence: ${Math.round(file.tag.confidence * 100)}%`,
          ``,
          `If that's wrong, type: type <correct-type>`,
          `or just rename it to whatever fits.`,
        ];
      }

      if (q.includes("flow") || q.includes("phase")) {
        return [
          `For a ${file.tag.type.toUpperCase()} file, the suggested flow is:`,
          `${file.flow}`,
          ``,
          `This is just a suggestion based on the type.`,
          `Your core actions (lock/split/sort/integrate) decide what actually runs.`,
        ];
      }

      if (q.includes("split") || q.includes("large")) {
        return [
          `${file.raw} has ${(file.tag as any).lines ?? "multiple"} lines.`,
          `When you run split, FlowStation will break it into`,
          `focused single-purpose modules automatically.`,
          `You'll review the result in the next dialog.`,
        ];
      }
    }

    // General questions about the plan
    if (q.includes("what") && q.includes("plan")) {
      return [
        `The plan is built from what we found in the scan.`,
        `It suggests which core actions to run and in what order.`,
        ``,
        `You see the full plan before anything runs.`,
        `You can reorder, remove, or add actions.`,
        `Nothing executes until you approve it.`,
      ];
    }

    if (q.includes("safe") || q.includes("risk")) {
      return [
        `Every action is logged in the audit trail.`,
        `Logic locks verify integrity after each phase.`,
        `You can verify any room at any time with: make verify`,
        ``,
        `If something goes wrong, the pipeline state records`,
        `exactly where it failed and resumes from there.`,
      ];
    }

    // Default — helpful redirect
    return [
      `I don't have a specific answer for that right now.`,
      ``,
      `If it's about this file: try type / rename / skip`,
      `If it's about the plan: we'll get there in the next step`,
      `If you need deep analysis: grant AI access after we lock`,
    ];
  }


  // ──────────────────────────────────────────────────────────
  //  STEP 5 — PLAN (build the action plan together)
  // ──────────────────────────────────────────────────────────

  private async stepPlan(): Promise<void> {
    this.clear();
    this.header("FlowStation — Action Plan");

    // Build plan from scan results
    this.ctx.plan = this.buildPlan();

    this.say("fluid", [
      `Based on what we reviewed, here's the plan I suggest.`,
      ``,
      `You can reorder, remove, or add actions before we run anything.`,
    ]);

    await this.showAndRefinePlan();
  }

  private async showAndRefinePlan(): Promise<void> {
    const plan = this.ctx.plan!;

    // Display the plan
    this.renderPlan(plan);

    console.log("");
    console.log(
      `${this.C.dim}  Options: ${this.C.reset}` +
      `${this.C.bold}approve${this.C.reset} · ` +
      `${this.C.bold}remove <number>${this.C.reset} · ` +
      `${this.C.bold}reorder <n> <n>${this.C.reset} · ` +
      `${this.C.bold}add <action>${this.C.reset} · ` +
      `${this.C.bold}note <text>${this.C.reset} · ` +
      `${this.C.bold}pause${this.C.reset}`
    );

    const input  = await this.ask("What do you want to do with this plan?");
    const intent = this.parseIntent(input);
    const lower  = input.trim().toLowerCase();

    // APPROVE
    if (intent === "approve" || this.isYes(input)) {
      await this.runStep("APPROVE");
      return;
    }

    // REMOVE action from plan
    if (intent === "remove" || lower.startsWith("remove ")) {
      const num = parseInt(lower.replace("remove", "").trim(), 10);
      if (!isNaN(num) && num >= 1 && num <= plan.actions.length) {
        const removed = plan.actions.splice(num - 1, 1)[0];
        this.reorderPlan();
        this.say("fluid", `🗑  Removed: ${removed.label}`);
      } else {
        this.say("fluid", `Enter a valid action number (1-${plan.actions.length})`);
      }
      await this.showAndRefinePlan();
      return;
    }

    // REORDER actions
    if (intent === "reorder" || lower.startsWith("reorder ")) {
      const parts = lower.replace("reorder", "").trim().split(/\s+/);
      const from  = parseInt(parts[0], 10) - 1;
      const to    = parseInt(parts[1], 10) - 1;

      if (
        !isNaN(from) && !isNaN(to) &&
        from >= 0 && to >= 0 &&
        from < plan.actions.length &&
        to < plan.actions.length
      ) {
        const [moved] = plan.actions.splice(from, 1);
        plan.actions.splice(to, 0, moved);
        this.reorderPlan();
        this.say("fluid", `↕  Reordered: moved ${moved.label} to position ${to + 1}`);
      } else {
        this.say("fluid", `Try: reorder 2 1  (move action 2 before action 1)`);
      }
      await this.showAndRefinePlan();
      return;
    }

    // ADD action
    if (intent === "add" || lower.startsWith("add ")) {
      const actionStr = lower.replace("add", "").trim();
      const validActions = ["lock", "split", "sort", "integrate", "verify"];
      if (validActions.includes(actionStr)) {
        plan.actions.push({
          type:      actionStr,
          room:      this.ctx.room,
          version:   this.ctx.version,
          label:     this.actionLabel(actionStr),
          reason:    "Added manually by user",
          confirmed: true,
          order:     plan.actions.length + 1,
        });
        this.say("fluid", `➕  Added: ${this.actionLabel(actionStr)}`);
      } else {
        this.say("fluid",
          `Unknown action. Valid: ${validActions.join(", ")}`
        );
      }
      await this.showAndRefinePlan();
      return;
    }

    // NOTE — add a note to the plan
    if (lower.startsWith("note ")) {
      const note = input.replace(/^note\s+/i, "").trim();
      plan.notes.push(note);
      this.say("fluid", `📝  Note added`);
      await this.showAndRefinePlan();
      return;
    }

    // QUESTION
    if (intent === "question" || input.startsWith("?")) {
      const question = input.replace(/^\?\s*/, "").trim();
      await this.handleQuestion(question, null);
      await this.showAndRefinePlan();
      return;
    }

    // PAUSE
    if (intent === "pause") {
      await this.runStep("PAUSED");
      return;
    }

    // ABORT
    if (intent === "abort") {
      this.abort();
      return;
    }

    // HELP
    if (intent === "help") {
      this.showHelp("PLAN");
      await this.showAndRefinePlan();
      return;
    }

    this.say("fluid", "Try: approve / remove <n> / reorder <n> <n> / add <action> / note <text>");
    await this.showAndRefinePlan();
  }

  private renderPlan(plan: DialogPlan): void {
    const { bold, cyan, dim, green, yellow, reset } = this.C;

    console.log(`\n${cyan}${bold}  Action Plan — ${plan.room} @ ${plan.version}${reset}\n`);
    console.log(`${dim}  ${"─".repeat(52)}${reset}`);

    for (const action of plan.actions) {
      const icon = this.actionIcon(action.type);
      console.log(
        `  ${dim}${action.order}.${reset}  ${icon}  ${bold}${action.label}${reset}`
      );
      console.log(
        `${dim}       ${action.reason}${reset}`
      );
    }

    if (plan.notes.length > 0) {
      console.log(`\n${dim}  Notes:${reset}`);
      for (const note of plan.notes) {
        console.log(`${dim}  📝 ${note}${reset}`);
      }
    }

    console.log(`\n${dim}  ${"─".repeat(52)}${reset}`);
    console.log(
      `${dim}  ${plan.actions.length} action(s) · ` +
      `${green}${plan.actions.filter(a => a.confirmed).length} confirmed${reset}` +
      `${dim} · Version: ${plan.version}${reset}`
    );
  }


  // ──────────────────────────────────────────────────────────
  //  STEP 6 — APPROVE
  // ──────────────────────────────────────────────────────────

  private async stepApprove(): Promise<void> {
    this.clear();
    this.header("FlowStation — Final Approval");

    const plan = this.ctx.plan!;
    this.renderPlan(plan);

    this.say("fluid", [
      ``,
      `This is your final check.`,
      ``,
      `Once you approve, your core actions will run in order.`,
      `You can watch each one live.`,
      `The audit log will record everything.`,
      ``,
      `${this.C.bold}There is no undo after execution starts.${this.C.reset}`,
      `But you can pause between actions.`,
    ]);

    const input = await this.ask(
      "Approve and execute this plan? (yes / back / pause / abort)"
    );

    const intent = this.parseIntent(input);

    if (intent === "approve" || this.isYes(input)) {
      plan.approvedAt = new Date().toISOString();
      this.say("fluid", `✅ Plan approved. Starting execution.`);
      await this.runStep("EXECUTE");
      return;
    }

    if (intent === "back") {
      await this.runStep("PLAN");
      return;
    }

    if (intent === "pause") {
      await this.runStep("PAUSED");
      return;
    }

    if (intent === "abort") {
      this.abort();
      return;
    }

    this.say("fluid", "Type yes to approve, back to adjust the plan, or abort to cancel.");
    await this.stepApprove();
  }


  // ──────────────────────────────────────────────────────────
  //  STEP 7 — EXECUTE
  // ──────────────────────────────────────────────────────────

  private async stepExecute(): Promise<void> {
    const plan = this.ctx.plan!;

    this.clear();
    this.header("FlowStation — Executing Plan");

    for (const action of plan.actions) {
      const icon = this.actionIcon(action.type);

      console.log(
        `\n${this.C.cyan}${this.C.bold}  ${icon} Running: ${action.label}${this.C.reset}`
      );
      console.log(`${this.C.dim}  ${"─".repeat(48)}${this.C.reset}`);

      try {
        // Run YOUR core action
        switch (action.type) {
          case "lock":
            await this.bridge.lock(action.room, action.version!);
            break;
          case "split":
            await this.bridge.split(action.room);
            break;
          case "sort":
            await this.bridge.sort(action.room);
            break;
          case "integrate":
            await this.bridge.integrate(action.room);
            break;
          case "verify":
            await this.bridge.verifyRoom(action.room);
            break;
        }

        console.log(
          `${this.C.green}  ✅ ${action.label} — done${this.C.reset}`
        );

        // Pause between actions — YOU decide to continue
        if (action.order < plan.actions.length) {
          const next = plan.actions[action.order]; // next action
          const cont = await this.ask(
            `Continue to: ${next?.label ?? "next step"}? (yes / pause / abort)`
          );

          if (this.parseIntent(cont) === "pause") {
            await this.runStep("PAUSED");
            return;
          }

          if (this.parseIntent(cont) === "abort") {
            this.say("fluid", "Execution stopped. Completed actions are saved.");
            await this.runStep("VERIFY");
            return;
          }
        }

      } catch (err) {
        const msg = (err as Error).message;
        console.log(`${this.C.red}  ❌ ${action.label} — failed${this.C.reset}`);
        console.log(`${this.C.dim}  ${msg}${this.C.reset}`);

        const choice = await this.ask(
          "Retry / skip this action / abort? (retry / skip / abort)"
        );

        const lower = choice.toLowerCase().trim();
        if (lower === "retry") {
          // Re-run same action
          plan.actions.unshift(action);
          await this.stepExecute();
          return;
        }

        if (lower === "skip") {
          this.say("fluid", "Skipping failed action and continuing.");
          continue;
        }

        this.say("fluid", "Execution stopped. Partial results are saved.");
        await this.runStep("VERIFY");
        return;
      }
    }

    // All done
    await this.runStep("VERIFY");
  }


  // ──────────────────────────────────────────────────────────
  //  STEP 8 — VERIFY
  // ──────────────────────────────────────────────────────────

  private async stepVerify(): Promise<void> {
    this.clear();
    this.header("FlowStation — Verify Results");

    this.say("fluid", [
      `Execution complete. Let's check the results.`,
    ]);

    // Check logic lock
    const lock = this.bridge.getLogicLock(this.ctx.room);
    if (lock) {
      console.log(`${this.C.green}  ✅ Logic lock found${this.C.reset}`);
      console.log(`${this.C.dim}     Status: ${(lock as any).status ?? "SEALED"}${this.C.reset}`);
    } else {
      console.log(`${this.C.yellow}  ⚠  No logic lock found yet${this.C.reset}`);
    }

    // Check mesh
    const rooms = this.bridge.listMeshRooms();
    if (rooms.includes(this.ctx.room)) {
      console.log(`${this.C.green}  ✅ Room in mesh${this.C.reset}`);
    } else {
      console.log(`${this.C.yellow}  ⚠  Room not in mesh yet${this.C.reset}`);
    }

    // Audit summary
    const auditEntries = this.bridge.getAuditByRoom(this.ctx.room, 5);
    console.log(`\n${this.C.dim}  Last ${auditEntries.length} audit entries:${this.C.reset}`);
    for (const entry of auditEntries) {
      console.log(`${this.C.dim}  ${entry.ts} · ${entry.action}${this.C.reset}`);
    }

    console.log("");
    const input = await this.ask(
      "How does it look? (done / run again / back to plan / pause)"
    );

    const lower = input.toLowerCase().trim();

    if (lower === "done" || this.isYes(input)) {
      await this.runStep("COMPLETE");
      return;
    }

    if (lower === "run again") {
      await this.runStep("PLAN");
      return;
    }

    if (lower === "back to plan" || lower === "back") {
      await this.runStep("PLAN");
      return;
    }

    if (this.parseIntent(input) === "pause") {
      await this.runStep("PAUSED");
      return;
    }

    await this.runStep("COMPLETE");
  }


  // ──────────────────────────────────────────────────────────
  //  STEP 9 — COMPLETE
  // ──────────────────────────────────────────────────────────

  private async stepComplete(): Promise<void> {
    this.clear();
    this.header("FlowStation — Complete");

    this.say("fluid", [
      ``,
      `That's a wrap on ${this.C.bold}${this.ctx.room}${this.C.reset}.`,
      ``,
      `Everything is logged. Logic lock is sealed.`,
      `The plan is saved in shared/dialog_plans/`,
      ``,
      `When you're ready for the next room, just start a new dialog.`,
    ]);

    // Save final plan
    this.savePlan();

    // Clean up saved dialog state — it's done
    this.clearDialogState();

    this.emit("complete", this.ctx.plan);
  }


  // ──────────────────────────────────────────────────────────
  //  PAUSED STATE
  // ──────────────────────────────────────────────────────────

  private stepPaused(): void {
    this.say("fluid", [
      ``,
      `Dialog paused and saved.`,
      ``,
      `Resume anytime with:`,
      `  ${this.C.bold}make fluid-dialog ROOM=${this.ctx.room} RESUME=true${this.C.reset}`,
      ``,
      `Your progress is saved at step: ${this.C.bold}${this.ctx.step}${this.C.reset}`,
    ]);

    this.saveDialogState();
    this.emit("paused", this.ctx);
  }


  // ──────────────────────────────────────────────────────────
  //  PLAN BUILDER
  // ──────────────────────────────────────────────────────────

  private buildPlan(): DialogPlan {
    const scan    = this.ctx.scan!;
    const actions: DialogAction[] = [];

    // Determine which phases are needed based on scan
    const hasCore    = scan.files.some(f => f.tag.type === "core");
    const hasAuth    = scan.files.some(f => f.tag.type === "auth");
    const hasConfig  = scan.files.some(f => f.tag.type === "config");
    const hasAPI     = scan.files.some(f => f.tag.type === "api");
    const largeFiles = scan.files.some(f => {
      const content = fs.readFileSync(f.path, "utf8");
      return content.split("\n").length > 200;
    });

    let order = 1;

    // LOCK — always first
    actions.push({
      type:      "lock",
      room:      this.ctx.room,
      version:   this.ctx.version,
      label:     `🔒 Lock ${this.ctx.room} @ ${this.ctx.version}`,
      reason:    "Snapshot and sign current state before changes",
      confirmed: true,
      order:     order++,
    });

    // SPLIT — if large files or multiple types
    if (largeFiles || scan.files.length > 5) {
      actions.push({
        type:      "split",
        room:      this.ctx.room,
        label:     `✂️  Split ${this.ctx.room} into modules`,
        reason:    largeFiles
          ? "Large files detected — split into focused modules"
          : "Multiple file types — split for clarity",
        confirmed: true,
        order:     order++,
      });
    }

    // SORT — if multiple types detected
    if (hasCore || hasAuth || hasConfig || hasAPI) {
      actions.push({
        type:      "sort",
        room:      this.ctx.room,
        label:     `🗂  Sort ${this.ctx.room} by category`,
        reason:    "Multiple categories found — sort for organization",
        confirmed: true,
        order:     order++,
      });
    }

    // INTEGRATE — always last
    actions.push({
      type:      "integrate",
      room:      this.ctx.room,
      label:     `🔗 Integrate ${this.ctx.room} into mesh`,
      reason:    "Wire sorted modules into the mesh with logic lock",
      confirmed: true,
      order:     order++,
    });

    return {
      room:       this.ctx.room,
      version:    this.ctx.version,
      actions,
      createdAt:  new Date().toISOString(),
      approvedAt: null,
      notes:      [],
      userOwns:   true,
    };
  }

  private reorderPlan(): void {
    const plan = this.ctx.plan!;
    plan.actions.forEach((a, i) => { a.order = i + 1; });
  }


  // ──────────────────────────────────────────────────────────
  //  PERSISTENCE
  // ──────────────────────────────────────────────────────────

  private dialogStatePath(): string {
    return path.join(
      this.bridge.getConfig().workspaceRoot,
      "shared",
      "dialog_state",
      `${this.ctx.room}.dialog.json`
    );
  }

  private saveDialogState(): void {
    const dir = path.dirname(this.dialogStatePath());
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    this.ctx.savedAt = new Date().toISOString();
    fs.writeFileSync(
      this.dialogStatePath(),
      JSON.stringify(this.ctx, null, 2),
      { encoding: "utf8", mode: 0o600 }
    );
  }

  private loadDialogState(): DialogContext | null {
    const p = this.dialogStatePath();
    if (!fs.existsSync(p)) return null;
    try {
      return JSON.parse(fs.readFileSync(p, "utf8"));
    } catch {
      return null;
    }
  }

  private clearDialogState(): void {
    const p = this.dialogStatePath();
    if (fs.existsSync(p)) fs.unlinkSync(p);
  }

  private savePlan(): void {
    if (!this.ctx.plan) return;

    const dir = path.join(
      this.bridge.getConfig().workspaceRoot,
      "shared",
      "dialog_plans"
    );
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    const filename = `${this.ctx.room}-${this.ctx.version}-${Date.now()}.plan.json`;
    fs.writeFileSync(
      path.join(dir, filename),
      JSON.stringify(this.ctx.plan, null, 2),
      "utf8"
    );
  }


  // ──────────────────────────────────────────────────────────
  //  UTILITIES
  // ──────────────────────────────────────────────────────────

  private ask(prompt: string): Promise<string> {
    return new Promise(resolve => {
      this.rl.question(
        `\n${this.C.cyan}${this.C.bold}  ❯ ${this.C.reset}${prompt}\n` +
        `${this.C.cyan}  › ${this.C.reset}`,
        answer => {
          // Log to history
          this.ctx.history.push({
            from:      "user",
            text:      answer,
            step:      this.ctx.step,
            timestamp: new Date().toISOString(),
          });
          resolve(answer.trim());
        }
      );
    });
  }

  private say(
    from:    "fluid" | "system",
    message: string | string[]
  ): void {
    const lines  = Array.isArray(message) ? message : [message];
    const prefix = from === "fluid"
      ? `${this.C.magenta}  ⚡ FlowStation${this.C.reset}`
      : `${this.C.dim}  system${this.C.reset}`;

    console.log("");
    console.log(prefix);
    for (const line of lines) {
      console.log(`${this.C.dim}  │${this.C.reset}  ${line}`);
    }

    // Log to history
    this.ctx.history.push({
      from,
      text:      lines.join("\n"),
      step:      this.ctx.step,
      timestamp: new Date().toISOString(),
    });
  }

  private parseIntent(input: string): UserIntent {
    const lower = input.toLowerCase().trim();

    if (["yes", "y", "confirm", "ok", "sure", "yep", "approved"].includes(lower))
      return "confirm";
    if (lower === "approve")              return "approve";
    if (lower.startsWith("rename"))       return "rename";
    if (["skip", "s", "next"].includes(lower)) return "skip";
    if (lower.startsWith("?") || lower.startsWith("question")) return "question";
    if (lower.startsWith("reorder"))      return "reorder";
    if (lower.startsWith("remove"))       return "remove";
    if (lower.startsWith("add"))          return "add";
    if (["pause", "save"].includes(lower)) return "pause";
    if (["abort", "cancel", "stop", "quit"].includes(lower)) return "abort";
    if (["back", "b", "prev"].includes(lower)) return "back";
    if (["help", "h", "?"].includes(lower)) return "help";

    return "confirm"; // default — let step handle it
  }

  private isYes(input: string): boolean {
    return ["yes", "y", "yep", "yup", "sure", "ok",
            "approve", "approved", "go", "run"].includes(
      input.toLowerCase().trim()
    );
  }

  private header(title: string): void {
    const { cyan, bold, reset } = this.C;
    console.log(
      `\n${cyan}${bold}╔══════════════════════════════════════════════════╗${reset}`
    );
    console.log(
      `${cyan}${bold}║  ⚡ ${title.padEnd(44)}║${reset}`
    );
    console.log(
      `${cyan}${bold}╚══════════════════════════════════════════════════╝${reset}`
    );
  }

  private box(lines: string[]): void {
    const { dim, reset } = this.C;
    console.log(`\n${dim}  ┌${"─".repeat(50)}┐${reset}`);
    for (const line of lines) {
      console.log(`${dim}  │${reset}  ${line}`);
    }
    console.log(`${dim}  └${"─".repeat(50)}┘${reset}`);
  }

  private progressBar(current: number, total: number): void {
    const width   = 30;
    const filled  = Math.round((current / total) * width);
    const empty   = width - filled;
    const bar     = "█".repeat(filled) + "░".repeat(empty);
    console.log(
      `\n${this.C.dim}  [${bar}] ${current}/${total}${this.C.reset}`
    );
  }

  private actionIcon(type: string): string {
    const icons: Record<string, string> = {
      lock:      "🔒",
      split:     "✂️ ",
      sort:      "🗂 ",
      integrate: "🔗",
      verify:    "🛡 ",
    };
    return icons[type] ?? "▸ ";
  }
  
  private actionLabel(type: string): string {
    const labels: Record<string, string> = {
      lock:      `🔒 Lock ${this.ctx.room}`,
      split:     `✂️  Split ${this.ctx.room}`,
      sort:      `🗂  Sort ${this.ctx.room}`,
      integrate: `🔗 Integrate ${this.ctx.room}`,
      verify:    `🛡  Verify ${this.ctx.room}`,
    };
    return labels[type] ?? type;
  }

  private abort(): void {
    this.say("fluid", [
      `Dialog cancelled.`,
      `No actions were run.`,
      `Your files are unchanged.`,
    ]);
    this.clearDialogState();
    this.emit("aborted");
    this.rl.close();
    process.exit(0);
  }

  private clear(): void {
    console.clear();
  }

  private showHelp(context: DialogStep): void {
    const { cyan, bold, dim, reset } = this.C;

    console.log(`\n${cyan}${bold}FlowStation Dialog Help${reset}\n`);

    if (context === "WELCOME") {
      console.log(`${dim}  At this step:${reset}`);
      console.log(`    ${bold}yes${reset}   - Start the scan`);
      console.log(`    ${bold}pause${reset} - Save and come back later`);
      console.log(`    ${bold}abort${reset} - Cancel everything`);
    }

    if (context === "REVIEW") {
      console.log(`${dim}  At this step (reviewing files):${reset}`);
      console.log(`    ${bold}yes${reset}              - Confirm this tag`);
      console.log(`    ${bold}rename <name>${reset}   - Change the label`);
      console.log(`    ${bold}type <type>${reset}     - Change the type (auth/core/api/etc)`);
      console.log(`    ${bold}skip${reset}             - Skip this file for now`);
      console.log(`    ${bold}? <question>${reset}    - Ask about this file`);
      console.log(`    ${bold}back${reset}             - Go to previous file`);
      console.log(`    ${bold}pause${reset}            - Save and come back later`);
      console.log(`    ${bold}abort${reset}            - Cancel dialog`);
    }

    if (context === "PLAN") {
      console.log(`${dim}  At this step (building plan):${reset}`);
      console.log(`    ${bold}approve${reset}         - Approve and execute the plan`);
      console.log(`    ${bold}remove <n>${reset}      - Remove action number n`);
      console.log(`    ${bold}reorder <n> <m>${reset} - Move action n to position m`);
      console.log(`    ${bold}add <action>${reset}    - Add lock/split/sort/integrate/verify`);
      console.log(`    ${bold}note <text>${reset}     - Add a note to the plan`);
      console.log(`    ${bold}? <question>${reset}    - Ask about the plan`);
      console.log(`    ${bold}pause${reset}            - Save and come back later`);
      console.log(`    ${bold}abort${reset}            - Cancel dialog`);
    }

    console.log(`\n${dim}  General commands (work anywhere):${reset}`);
    console.log(`    ${bold}help${reset}  - Show this help`);
    console.log(`    ${bold}pause${reset} - Save current state and exit`);
    console.log(`    ${bold}abort${reset} - Cancel the entire dialog`);

    console.log(`\n${dim}  Remember:${reset}`);
    console.log(`    - AI suggests. YOU decide.`);
    console.log(`    - Nothing runs without your approval.`);
    console.log(`    - Dialog state auto-saves at every step.`);
    console.log(`    - Core actions (lock/split/sort/integrate) are always yours.`);
    console.log("");
  }

  /**
   * Destroy dialog and clean up.
   */
  destroy(): void {
    this.rl.close();
    this.removeAllListeners();
  }
}
    
    