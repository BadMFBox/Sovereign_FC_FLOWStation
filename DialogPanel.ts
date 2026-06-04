// ═══════════════════════════════════════════════════════════════
//  DialogPanel.ts
//  Fluid dialog rendered as a VS Code webview panel
//  Real plan-based conversation inside VS Code
// ═══════════════════════════════════════════════════════════════

import * as vscode       from "vscode";
import * as path         from "path";
import { BridgeConnector } from "./BridgeConnector";
import { SessionManager }  from "./SessionManager";
import {
  FluidDialog,
  DialogPlan,
  DialogStep,
  DialogMessage
} from "./FluidDialog";

export class DialogPanel {

  static currentPanel: DialogPanel | undefined;
  private readonly panel: vscode.WebviewPanel;
  private dialog: FluidDialog | null = null;

  // ── Factory ─────────────────────────────────────────────────

  static open(
    context: vscode.ExtensionContext,
    bridge:  BridgeConnector,
    session: SessionManager,
    room:    string,
    version: string,
    resume:  boolean = false
  ): DialogPanel {
    if (DialogPanel.currentPanel) {
      DialogPanel.currentPanel.panel.reveal(vscode.ViewColumn.One);
      return DialogPanel.currentPanel;
    }

    const panel = vscode.window.createWebviewPanel(
      "flowstationDialog",
      `⚡ FlowStation — ${room}`,
      vscode.ViewColumn.One,
      {
        enableScripts:             true,
        retainContextWhenHidden:   true,
        localResourceRoots: [
          vscode.Uri.joinPath(context.extensionUri, "src", "media")
        ]
      }
    );

    DialogPanel.currentPanel = new DialogPanel(
      panel, context, bridge, session, room, version, resume
    );

    return DialogPanel.currentPanel;
  }

  // ── Constructor ─────────────────────────────────────────────

  private constructor(
    panel:           vscode.WebviewPanel,
    context:         vscode.ExtensionContext,
    private bridge:  BridgeConnector,
    private session: SessionManager,
    private room:    string,
    private version: string,
    private resume:  boolean
  ) {
    this.panel = panel;

    // Render initial HTML
    this.panel.webview.html = this.getHtml();

    // Handle messages FROM webview
    this.panel.webview.onDidReceiveMessage(
      msg => this.handleWebviewMessage(msg),
      undefined,
      context.subscriptions
    );

    // Cleanup on close
    this.panel.onDidDispose(
      () => { DialogPanel.currentPanel = undefined; },
      null,
      context.subscriptions
    );

    // Start the dialog
    this.startDialog();
  }

  // ── Dialog Integration ───────────────────────────────────────

  private async startDialog(): Promise<void> {
    this.dialog = new FluidDialog(this.bridge, {
      room:    this.room,
      version: this.version,
      resume:  this.resume,
    });

    // Pipe dialog events to webview
    this.dialog.on("message", (msg: DialogMessage) => {
      this.postToWebview({ type: "message", payload: msg });
    });

    this.dialog.on("stepChange", (step: DialogStep) => {
      this.postToWebview({ type: "stepChange", payload: step });
    });

    this.dialog.on("planReady", (plan: DialogPlan) => {
      this.postToWebview({ type: "planReady", payload: plan });
    });

    this.dialog.on("complete", (plan: DialogPlan) => {
      this.postToWebview({ type: "complete", payload: plan });
      vscode.window.showInformationMessage(
        `✅ FlowStation: ${this.room} dialog complete`,
        "View Plan"
      ).then(choice => {
        if (choice === "View Plan") {
          this.postToWebview({ type: "showPlan", payload: plan });
        }
      });
    });

    this.dialog.on("paused", () => {
      this.postToWebview({ type: "paused" });
      vscode.window.showInformationMessage(
        `⏸  FlowStation: Dialog paused for ${this.room}`
      );
    });

    this.dialog.on("aborted", () => {
      this.postToWebview({ type: "aborted" });
      this.panel.dispose();
    });

    // Start
    await this.dialog.start();
  }

  // ── Message Handler ─────────────────────────────────────────

  private handleWebviewMessage(msg: {
    type:    string;
    payload: unknown;
  }): void {

    switch (msg.type) {

      case "userInput":
        // User typed something in the dialog UI
        this.dialog?.receiveInput(msg.payload as string);
        break;

      case "quickAction":
        // User clicked a quick-action button
        const action = msg.payload as string;
        this.dialog?.receiveInput(action);
        break;

      case "requestState":
        // Webview asking for current state
        this.postToWebview({
          type:    "state",
          payload: this.dialog?.getContext()
        });
        break;

      case "abort":
        this.dialog?.receiveInput("abort");
        break;

      case "pause":
        this.dialog?.receiveInput("pause");
        break;
    }
  }

  private postToWebview(msg: object): void {
    this.panel.webview.postMessage(msg);
  }

  // ── Webview HTML ─────────────────────────────────────────────

  private getHtml(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FlowStation Dialog</title>
  <style>
    /* ── Reset ── */
    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: var(--vscode-font-family);
      font-size:   var(--vscode-font-size);
      color:       var(--vscode-foreground);
      background:  var(--vscode-editor-background);
      height:      100vh;
      display:     flex;
      flex-direction: column;
      overflow:    hidden;
    }

    /* ── Header ── */
    .header {
      padding:          12px 16px;
      border-bottom:    1px solid var(--vscode-panel-border);
      display:          flex;
      align-items:      center;
      justify-content:  space-between;
      background:       var(--vscode-sideBar-background);
    }

    .header-title {
      font-size:   14px;
      font-weight: 600;
      color:       var(--vscode-foreground);
      display:     flex;
      align-items: center;
      gap:         8px;
    }

    .header-step {
      font-size:  11px;
      padding:    2px 8px;
      border-radius: 10px;
      background: var(--vscode-badge-background);
      color:      var(--vscode-badge-foreground);
    }

    /* ── Step Progress ── */
    .steps {
      display:     flex;
      padding:     8px 16px;
      gap:         4px;
      background:  var(--vscode-sideBar-background);
      border-bottom: 1px solid var(--vscode-panel-border);
      overflow-x:  auto;
    }

    .step-pill {
      font-size:     10px;
      padding:       3px 10px;
      border-radius: 10px;
      white-space:   nowrap;
      background:    var(--vscode-input-background);
      color:         var(--vscode-descriptionForeground);
      border:        1px solid transparent;
      transition:    all 0.2s;
    }

    .step-pill.active {
      background: var(--vscode-button-background);
      color:      var(--vscode-button-foreground);
      font-weight: 600;
    }

    .step-pill.done {
      background: transparent;
      color:      var(--vscode-charts-green);
      border-color: var(--vscode-charts-green);
    }

    /* ── Messages ── */
    .messages {
      flex:       1;
      overflow-y: auto;
      padding:    16px;
      display:    flex;
      flex-direction: column;
      gap:        12px;
      scroll-behavior: smooth;
    }

    .message {
      display:        flex;
      flex-direction: column;
      gap:            4px;
      max-width:      85%;
      animation:      fadeIn 0.2s ease;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .message.fluid {
      align-self: flex-start;
    }

    .message.user {
      align-self: flex-end;
    }

    .message-label {
      font-size: 10px;
      color:     var(--vscode-descriptionForeground);
      padding:   0 4px;
    }

    .message-bubble {
      padding:       10px 14px;
      border-radius: 8px;
      line-height:   1.6;
      white-space:   pre-wrap;
      font-size:     13px;
    }

    .message.fluid .message-bubble {
      background:    var(--vscode-sideBar-background);
      border:        1px solid var(--vscode-panel-border);
      border-left:   3px solid var(--vscode-charts-blue);
      color:         var(--vscode-foreground);
    }

    .message.user .message-bubble {
      background:    var(--vscode-button-background);
      color:         var(--vscode-button-foreground);
    }

    /* ── Plan Card ── */
    .plan-card {
      background:    var(--vscode-sideBar-background);
      border:        1px solid var(--vscode-panel-border);
      border-radius: 8px;
      padding:       16px;
      width:         100%;
    }

    .plan-card h3 {
      font-size:     13px;
      margin-bottom: 12px;
      color:         var(--vscode-foreground);
    }

    .plan-action {
      display:     flex;
      align-items: flex-start;
      gap:         12px;
      padding:     8px 0;
      border-bottom: 1px solid var(--vscode-panel-border);
    }

    .plan-action:last-child {
      border-bottom: none;
    }

    .plan-action-num {
      font-size:  11px;
      color:      var(--vscode-descriptionForeground);
      min-width:  20px;
      margin-top: 2px;
    }

    .plan-action-body { flex: 1; }

    .plan-action-label {
      font-weight: 600;
      font-size:   13px;
    }

    .plan-action-reason {
      font-size: 11px;
      color:     var(--vscode-descriptionForeground);
      margin-top: 2px;
    }

    .plan-note {
      margin-top: 12px;
      padding:    8px 12px;
      background: var(--vscode-input-background);
      border-radius: 4px;
      font-size:  11px;
      color:      var(--vscode-foreground);
    }

    /* ── Quick Actions ── */
    .quick-actions {
      display:    flex;
      flex-wrap:  wrap;
      gap:        6px;
      padding:    8px 16px;
      background: var(--vscode-sideBar-background);
      border-top: 1px solid var(--vscode-panel-border);
    }

    .quick-btn {
      font-size:     11px;
      padding:       4px 12px;
      border-radius: 4px;
      border:        1px solid var(--vscode-button-secondaryBackground);
      background:    var(--vscode-button-secondaryBackground);
      color:         var(--vscode-button-secondaryForeground);
      cursor:        pointer;
      transition:    all 0.15s;
      font-family:   var(--vscode-font-family);
    }

    .quick-btn:hover {
      background: var(--vscode-button-secondaryHoverBackground);
    }

    .quick-btn.primary {
      background: var(--vscode-button-background);
      color:      var(--vscode-button-foreground);
      border-color: var(--vscode-button-background);
    }

    .quick-btn.primary:hover {
      background: var(--vscode-button-hoverBackground);
    }

    .quick-btn.danger {
      border-color: var(--vscode-charts-red);
      color:        var(--vscode-charts-red);
    }

    /* ── Input ── */
    .input-area {
      display:       flex;
      gap:           8px;
      padding:       12px 16px;
      background:    var(--vscode-sideBar-background);
      border-top:    1px solid var(--vscode-panel-border);
      align-items:   center;
    }

    .input-field {
      flex:          1;
      padding:       8px 12px;
      background:    var(--vscode-input-background);
      color:         var(--vscode-input-foreground);
      border:        1px solid var(--vscode-input-border);
      border-radius: 4px;
      font-family:   var(--vscode-font-family);
      font-size:     13px;
      outline:       none;
    }

    .input-field:focus {
      border-color: var(--vscode-focusBorder);
    }

    .send-btn {
      padding:       8px 14px;
      background:    var(--vscode-button-background);
      color:         var(--vscode-button-foreground);
      border:        none;
      border-radius: 4px;
      cursor:        pointer;
      font-size:     13px;
      font-family:   var(--vscode-font-family);
    }

    .send-btn:hover {
      background: var(--vscode-button-hoverBackground);
    }

    .send-btn:disabled {
      opacity: 0.5;
      cursor:  not-allowed;
    }

    /* ── Progress bar ── */
    .progress-bar {
      height:       3px;
      background:   var(--vscode-input-background);
      border-radius: 2px;
      margin:       8px 0;
      overflow:     hidden;
    }

    .progress-fill {
      height:       100%;
      background:   var(--vscode-charts-blue);
      border-radius: 2px;
      transition:   width 0.3s ease;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
      background:    var(--vscode-scrollbarSlider-background);
      border-radius: 2px;
    }
  </style>
</head>
<body>

  <!-- Header -->
  <div class="header">
    <div class="header-title">
      ⚡ FlowStation
      <span class="header-step" id="currentStep">WELCOME</span>
    </div>
    <div style="display:flex;gap:8px;">
      <button class="quick-btn" onclick="sendQuickAction('help')">Help</button>
      <button class="quick-btn" onclick="sendQuickAction('pause')">Pause</button>
      <button class="quick-btn danger" onclick="sendQuickAction('abort')">Abort</button>
    </div>
  </div>

  <!-- Step pills -->
  <div class="steps">
    <div class="step-pill active" id="step-WELCOME">Welcome</div>
    <div class="step-pill"        id="step-SCAN">Scan</div>
    <div class="step-pill"        id="step-REVIEW">Review</div>
    <div class="step-pill"        id="step-PLAN">Plan</div>
    <div class="step-pill"        id="step-APPROVE">Approve</div>
    <div class="step-pill"        id="step-EXECUTE">Execute</div>
    <div class="step-pill"        id="step-VERIFY">Verify</div>
    <div class="step-pill"        id="step-COMPLETE">Complete</div>
  </div>

  <!-- Message feed -->
  <div class="messages" id="messages"></div>

  <!-- Quick actions (context-sensitive) -->
  <div class="quick-actions" id="quickActions">
    <button class="quick-btn primary" onclick="sendQuickAction('yes')">Yes ✓</button>
    <button class="quick-btn"         onclick="sendQuickAction('skip')">Skip</button>
    <button class="quick-btn"         onclick="sendQuickAction('back')">← Back</button>
    <button class="quick-btn"         onclick="sendQuickAction('help')">Help</button>
  </div>

  <!-- Input -->
  <div class="input-area">
    <input
      class="input-field"
      id="inputField"
      type="text"
      placeholder="Type your response..."
      autocomplete="off"
      autofocus
    />
    <button class="send-btn" id="sendBtn" onclick="sendInput()">Send</button>
  </div>

  <script>
    const vscode = acquireVsCodeApi();

    // ── State ──────────────────────────────────────────────────
    let currentStep = 'WELCOME';
    let isWaiting   = false;

    const STEP_ORDER = [
      'WELCOME','SCAN','REVIEW','PLAN',
      'APPROVE','EXECUTE','VERIFY','COMPLETE'
    ];

    // ── Send user input ────────────────────────────────────────
    function sendInput() {
      const field = document.getElementById('inputField');
      const value = field.value.trim();
      if (!value || isWaiting) return;

      addMessage('user', value);
      vscode.postMessage({ type: 'userInput', payload: value });
      field.value = '';
      setWaiting(true);
    }

    function sendQuickAction(action) {
      if (isWaiting) return;
      addMessage('user', action);
      vscode.postMessage({ type: 'quickAction', payload: action });
      setWaiting(true);
    }

    function setWaiting(val) {
      isWaiting = val;
      document.getElementById('sendBtn').disabled = val;
      document.getElementById('inputField').disabled = val;
    }

    // ── Add a message bubble ───────────────────────────────────
    function addMessage(from, text) {
      const messages = document.getElementById('messages');

      const wrapper = document.createElement('div');
      wrapper.className = 'message ' + from;

      const label = document.createElement('div');
      label.className = 'message-label';
      label.textContent = from === 'fluid'
        ? '⚡ FlowStation'
        : 'You';

      const bubble = document.createElement('div');
      bubble.className = 'message-bubble';
      bubble.textContent = text;

      wrapper.appendChild(label);
      wrapper.appendChild(bubble);
      messages.appendChild(wrapper);

      // Auto-scroll
      messages.scrollTop = messages.scrollHeight;
    }

    // ── Render a plan card ─────────────────────────────────────
    function renderPlan(plan) {
      const messages = document.getElementById('messages');

      const card = document.createElement('div');
      card.className = 'plan-card';

      card.innerHTML = '<h3>📋 Action Plan — ' +
        plan.room + ' @ ' + plan.version + '</h3>';

      for (const action of plan.actions) {
        const row = document.createElement('div');
        row.className = 'plan-action';
        row.innerHTML =
          '<div class="plan-action-num">' + action.order + '.</div>' +
          '<div class="plan-action-body">' +
            '<div class="plan-action-label">' + action.label + '</div>' +
            '<div class="plan-action-reason">' + action.reason + '</div>' +
          '</div>';
        card.appendChild(row);
      }

      if (plan.notes && plan.notes.length > 0) {
        for (const note of plan.notes) {
          const n = document.createElement('div');
          n.className = 'plan-note';
          n.textContent = '📝 ' + note;
          card.appendChild(n);
        }
      }

      const wrapper = document.createElement('div');
      wrapper.className = 'message fluid';
      wrapper.appendChild(card);
      messages.appendChild(wrapper);
      messages.scrollTop = messages.scrollHeight;
    }
    
    // ── Update step indicators ─────────────────────────────────
    function updateStep(step) {
      currentStep = step;

      const stepIdx = STEP_ORDER.indexOf(step);

      STEP_ORDER.forEach((s, i) => {
        const el = document.getElementById('step-' + s);
        if (!el) return;
        el.className = 'step-pill';
        if (i < stepIdx)  el.classList.add('done');
        if (i === stepIdx) el.classList.add('active');
      });

      document.getElementById('currentStep').textContent = step;
      updateQuickActions(step);
    }

    // ── Update quick action buttons per step ───────────────────
    function updateQuickActions(step) {
      const qa = document.getElementById('quickActions');

      const actionMap = {
        WELCOME: [
          { label: 'Yes ✓', action: 'yes',   cls: 'primary' },
          { label: 'Pause', action: 'pause',  cls: '' },
          { label: 'Abort', action: 'abort',  cls: 'danger' },
        ],
        SCAN: [
          { label: 'Yes ✓', action: 'yes',   cls: 'primary' },
          { label: 'Pause', action: 'pause',  cls: '' },
        ],
        REVIEW: [
          { label: 'Yes ✓',    action: 'yes',    cls: 'primary' },
          { label: 'Skip',     action: 'skip',   cls: '' },
          { label: '← Back',  action: 'back',   cls: '' },
          { label: '? Ask',   action: '? ',      cls: '' },
          { label: 'Pause',   action: 'pause',   cls: '' },
        ],
        PLAN: [
          { label: 'Approve ✓', action: 'approve', cls: 'primary' },
          { label: 'Pause',     action: 'pause',   cls: '' },
          { label: 'Abort',     action: 'abort',   cls: 'danger' },
        ],
        APPROVE: [
          { label: 'Yes — Execute', action: 'yes',   cls: 'primary' },
          { label: '← Back',       action: 'back',  cls: '' },
          { label: 'Abort',        action: 'abort', cls: 'danger' },
        ],
        EXECUTE: [
          { label: 'Continue ✓', action: 'yes',   cls: 'primary' },
          { label: 'Pause',      action: 'pause', cls: '' },
          { label: 'Abort',      action: 'abort', cls: 'danger' },
        ],
        VERIFY: [
          { label: 'Done ✓',     action: 'done',       cls: 'primary' },
          { label: 'Run Again',  action: 'run again',  cls: '' },
          { label: '← Back',    action: 'back',        cls: '' },
        ],
        COMPLETE: [
          { label: 'Close',      action: 'close',      cls: 'primary' },
        ],
      };

      const actions = actionMap[step] ?? actionMap.WELCOME;

      qa.innerHTML = actions.map(a =>
        '<button class="quick-btn ' + a.cls + '" ' +
        'onclick="sendQuickAction(\'' + a.action + '\')">' +
        a.label + '</button>'
      ).join('');
    }

    // ── Handle messages FROM extension ────────────────────────
    window.addEventListener('message', event => {
      const { type, payload } = event.data;

      switch (type) {

        case 'message':
          // FlowStation dialog message
          if (Array.isArray(payload.lines)) {
            addMessage('fluid', payload.lines.join('\n'));
          } else if (payload.text) {
            addMessage('fluid', payload.text);
          }
          setWaiting(false);
          break;

        case 'stepChange':
          updateStep(payload);
          setWaiting(false);
          break;

        case 'planReady':
        case 'showPlan':
          renderPlan(payload);
          setWaiting(false);
          break;

        case 'complete':
          renderPlan(payload);
          updateStep('COMPLETE');
          setWaiting(false);
          addMessage('fluid', '✅ Dialog complete. Plan saved.');
          break;

        case 'paused':
          addMessage('fluid', '⏸  Dialog paused. State saved.\nResume anytime with: make fluid-resume ROOM=' + (payload ?? ''));
          setWaiting(false);
          break;

        case 'aborted':
          addMessage('fluid', '❌ Dialog aborted. No actions were run.');
          setWaiting(false);
          break;

        case 'state':
          if (payload?.step) updateStep(payload.step);
          setWaiting(false);
          break;
      }
    });

    // ── Enter key to send ──────────────────────────────────────
    document.getElementById('inputField')
      .addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendInput();
        }
      });

    // ── Request initial state ──────────────────────────────────
    vscode.postMessage({ type: 'requestState' });
  </script>
</body>
</html>`;
  }
}
      
