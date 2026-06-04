// ═══════════════════════════════════════════════════════════════
//  SessionPanel.ts
//  Main sidebar webview — command center + live session state
//  AiZQuad FlowStation Lab
//  Founder: Juan Jaime Rivera Zamorano
// ═══════════════════════════════════════════════════════════════

import * as vscode        from "vscode";
import { BridgeConnector } from "./BridgeConnector";
import { SessionManager }  from "./SessionManager";

export class SessionPanel implements vscode.WebviewViewProvider {

  private view?: vscode.WebviewView;
  private updateInterval: ReturnType<typeof setInterval> | null = null;

  constructor(
    private context: vscode.ExtensionContext,
    private bridge:  BridgeConnector,
    private session: SessionManager
  ) {
    // Listen to session events
    session.on("unlocked", () => this.render());
    session.on("locked",   () => this.render());
    session.on("expired",  () => this.render());
  }

  // ── WebviewViewProvider Implementation ──────────────────────

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context:    vscode.WebviewViewResolveContext,
    _token:      vscode.CancellationToken
  ): void | Thenable<void> {

    this.view = webviewView;

    // Configure webview
    webviewView.webview.options = {
      enableScripts:      true,
      localResourceRoots: [
        vscode.Uri.joinPath(this.context.extensionUri, "src", "media")
      ]
    };

    // Handle messages FROM webview
    webviewView.webview.onDidReceiveMessage(
      msg => this.handleMessage(msg)
    );

    // Render initial content
    this.render();

    // Update every 1 second (for timer countdown)
    this.updateInterval = setInterval(() => {
      if (this.session.isUnlocked()) {
        this.postMessage({
          type:    "sessionUpdate",
          payload: this.session.getInfo()
        });
      }
    }, 1000);

    // Cleanup on dispose
    webviewView.onDidDispose(() => {
      if (this.updateInterval) {
        clearInterval(this.updateInterval);
        this.updateInterval = null;
      }
    });
  }

  // ── Public API ──────────────────────────────────────────────

  render(): void {
    if (!this.view) return;
    this.view.webview.html = this.getHtml();
  }

  // ── Private ─────────────────────────────────────────────────

  private handleMessage(msg: {
    type:    string;
    payload?: unknown;
  }): void {

    switch (msg.type) {

      case "unlock":
        vscode.commands.executeCommand("flowstation.unlock");
        break;

      case "lock":
        vscode.commands.executeCommand("flowstation.lock");
        break;

      case "openDialog":
        vscode.commands.executeCommand("flowstation.openDialog");
        break;

      case "refreshRooms":
        vscode.commands.executeCommand("flowstation.refreshRooms");
        break;

      case "viewAudit":
        vscode.commands.executeCommand("flowstation.viewAudit");
        break;

      case "quickAction": {
        const action = msg.payload as string;
        this.handleQuickAction(action);
        break;
      }

      case "requestUpdate":
        this.postMessage({
          type:    "sessionUpdate",
          payload: this.session.getInfo()
        });
        this.postMessage({
          type:    "statsUpdate",
          payload: this.getStats()
        });
        break;
    }
  }

  private async handleQuickAction(action: string): Promise<void> {
    const rooms = this.bridge.listActiveRooms();

    switch (action) {

      case "lock_first_room": {
        if (rooms.length === 0) {
          vscode.window.showErrorMessage("No rooms found");
          return;
        }
        const room = rooms[0];
        const version = await vscode.window.showInputBox({
          prompt:      `Lock ${room} — enter version`,
          value:       "v1",
          placeHolder: "e.g. v1, v2.1"
        });
        if (!version) return;
        vscode.commands.executeCommand(
          "flowstation.lockRoom",
          { roomName: room }
        );
        break;
      }

      case "verify_all": {
        const confirm = await vscode.window.showWarningMessage(
          "Verify all locked rooms?",
          { modal: true },
          "Verify"
        );
        if (confirm !== "Verify") return;

        const lockedRooms = rooms.filter(r =>
          this.bridge.isRoomLocked(r)
        );

        if (lockedRooms.length === 0) {
          vscode.window.showInformationMessage("No locked rooms to verify");
          return;
        }

        for (const room of lockedRooms) {
          await vscode.commands.executeCommand(
            "flowstation.verifyRoom",
            { roomName: room }
          );
        }
        break;
      }

      case "open_dialog": {
        vscode.commands.executeCommand("flowstation.openDialog");
        break;
      }

      case "view_audit": {
        vscode.commands.executeCommand("flowstation.viewAudit");
        break;
      }
    }
  }

  private postMessage(msg: object): void {
    this.view?.webview.postMessage(msg);
  }

  private getStats(): {
    totalRooms:   number;
    lockedRooms:  number;
    activeRooms:  number;
    integratedRooms: number;
    recentEvents: number;
  } {
    const rooms   = this.bridge.listActiveRooms();
    const locked  = rooms.filter(r => this.bridge.isRoomLocked(r));
    const phases  = rooms.map(r => this.bridge.getRoomPhases(r));
    const integrated = phases.filter(p => p.integrated);
    const audit   = this.bridge.getRecentAuditRaw(10);

    return {
      totalRooms:   rooms.length,
      lockedRooms:  locked.length,
      activeRooms:  rooms.length - locked.length,
      integratedRooms: integrated.length,
      recentEvents: audit.length,
    };
  }

  // ── HTML Generation ─────────────────────────────────────────

  private getHtml(): string {
    const sessionInfo = this.session.getInfo();
    const stats       = this.getStats();

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FlowStation Session</title>
  <style>
    /* ── Reset ── */
    * {
      box-sizing: border-box;
      margin:     0;
      padding:    0;
    }

    body {
      font-family: var(--vscode-font-family);
      font-size:   var(--vscode-font-size);
      color:       var(--vscode-foreground);
      background:  var(--vscode-sideBar-background);
      padding:     16px;
      overflow-y:  auto;
      height:      100vh;
    }

    /* ── Header ── */
    .header {
      display:         flex;
      align-items:     center;
      justify-content: space-between;
      margin-bottom:   20px;
      padding-bottom:  16px;
      border-bottom:   2px solid var(--vscode-panel-border);
    }

    .header-logo {
      font-size:   18px;
      font-weight: 700;
      color:       var(--vscode-foreground);
      display:     flex;
      align-items: center;
      gap:         8px;
    }

    .header-logo::before {
      content:     "⚡";
      font-size:   24px;
      display:     inline-block;
    }

    .header-version {
      font-size:  10px;
      padding:    2px 6px;
      background: var(--vscode-badge-background);
      color:      var(--vscode-badge-foreground);
      border-radius: 4px;
    }

    /* ── Session Card ── */
    .session-card {
      background:    var(--vscode-editor-background);
      border:        1px solid var(--vscode-panel-border);
      border-radius: 8px;
      padding:       16px;
      margin-bottom: 16px;
    }

    .session-card.locked {
      border-left: 4px solid var(--vscode-charts-red);
    }

    .session-card.unlocked {
      border-left: 4px solid var(--vscode-charts-green);
    }

    .session-card.expired {
      border-left: 4px solid var(--vscode-charts-orange);
    }

    .session-status {
      display:         flex;
      align-items:     center;
      justify-content: space-between;
      margin-bottom:   12px;
    }

    .session-label {
      font-size:   13px;
      font-weight: 600;
      color:       var(--vscode-foreground);
      display:     flex;
      align-items: center;
      gap:         8px;
    }

    .session-icon {
      font-size: 16px;
    }

    .session-timer {
      font-size:      16px;
      font-weight:    700;
      font-variant-numeric: tabular-nums;
      color:          var(--vscode-charts-yellow);
    }

    .session-meta {
      font-size:  11px;
      color:      var(--vscode-descriptionForeground);
      margin-top: 8px;
    }

    .session-actions {
      display:    flex;
      gap:        8px;
      margin-top: 12px;
    }

    .btn {
      flex:          1;
      padding:       8px 12px;
      border:        none;
      border-radius: 4px;
      font-size:     12px;
      font-weight:   600;
      font-family:   var(--vscode-font-family);
      cursor:        pointer;
      transition:    all 0.15s;
      text-align:    center;
    }

    .btn-primary {
      background: var(--vscode-button-background);
      color:      var(--vscode-button-foreground);
    }

    .btn-primary:hover {
      background: var(--vscode-button-hoverBackground);
    }

    .btn-secondary {
      background: var(--vscode-button-secondaryBackground);
      color:      var(--vscode-button-secondaryForeground);
    }

    .btn-secondary:hover {
      background: var(--vscode-button-secondaryHoverBackground);
    }

    /* ── Stats Grid ── */
    .stats-grid {
      display:               grid;
      grid-template-columns: repeat(2, 1fr);
      gap:                   12px;
      margin-bottom:         16px;
    }

    .stat-card {
      background:    var(--vscode-editor-background);
      border:        1px solid var(--vscode-panel-border);
      border-radius: 6px;
      padding:       12px;
      display:       flex;
      flex-direction: column;
      gap:           6px;
    }

    .stat-label {
      font-size: 10px;
      color:     var(--vscode-descriptionForeground);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .stat-value {
      font-size:   20px;
      font-weight: 700;
      color:       var(--vscode-foreground);
    }

    .stat-icon {
      font-size: 14px;
      opacity:   0.7;
    }

    /* ── Quick Actions ── */
    .quick-actions {
      margin-bottom: 16px;
    }

    .section-title {
      font-size:     11px;
      font-weight:   600;
      color:         var(--vscode-descriptionForeground);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 8px;
    }

    .action-list {
      display:        flex;
      flex-direction: column;
      gap:            6px;
    }

    .action-btn {
      background:     var(--vscode-list-hoverBackground);
      border:         1px solid var(--vscode-panel-border);
      border-radius:  4px;
      padding:        10px 12px;
      font-size:      12px;
      font-family:    var(--vscode-font-family);
      color:          var(--vscode-foreground);
      cursor:         pointer;
      display:        flex;
      align-items:    center;
      justify-content: space-between;
      transition:     all 0.15s;
    }

    .action-btn:hover {
      background: var(--vscode-list-activeSelectionBackground);
      color:      var(--vscode-list-activeSelectionForeground);
    }

    .action-btn-label {
      display:     flex;
      align-items: center;
      gap:         8px;
    }

    .action-btn-icon {
      font-size: 14px;
    }

    .action-btn-arrow {
      font-size: 10px;
      opacity:   0.5;
    }

    /* ── Footer ── */
    .footer {
      margin-top:  24px;
      padding-top: 12px;
      border-top:  1px solid var(--vscode-panel-border);
      font-size:   10px;
      color:       var(--vscode-descriptionForeground);
      text-align:  center;
    }

    .footer a {
      color:           var(--vscode-textLink-foreground);
      text-decoration: none;
    }

    .footer a:hover {
      text-decoration: underline;
    }

    /* ── Progress ring (timer visual) ── */
    .progress-ring {
      width:  60px;
      height: 60px;
      margin: 0 auto 12px;
    }

    .progress-ring-circle {
      stroke:           var(--vscode-charts-yellow);
      stroke-width:     4;
      fill:             transparent;
      stroke-dasharray: 188.5;
      stroke-dashoffset: 0;
      transform:        rotate(-90deg);
      transform-origin: center;
      transition:       stroke-dashoffset 0.5s ease;
    }

    /* ── Animations ── */
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50%      { opacity: 0.6; }
    }

    .pulse {
      animation: pulse 2s ease-in-out infinite;
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
    <div class="header-logo">
      FlowStation
      <span class="header-version">v1.0</span>
    </div>
  </div>

  <!-- Session Card -->
  <div class="session-card ${sessionInfo.state}" id="sessionCard">
    
    ${this.renderSessionContent(sessionInfo)}

  </div>

  <!-- Stats Grid -->
  <div class="stats-grid">
    
    <div class="stat-card">
      <div class="stat-label">
        <span class="stat-icon">📦</span> Total Rooms
      </div>
      <div class="stat-value" id="statTotalRooms">${stats.totalRooms}</div>
    </div>

    <div class="stat-card">
      <div class="stat-label">
        <span class="stat-icon">🔒</span> Locked
      </div>
      <div class="stat-value" id="statLockedRooms">${stats.lockedRooms}</div>
    </div>

    <div class="stat-card">
      <div class="stat-label">
        <span class="stat-icon">🔓</span> Active
      </div>
      <div class="stat-value" id="statActiveRooms">${stats.activeRooms}</div>
    </div>

    <div class="stat-card">
      <div class="stat-label">
        <span class="stat-icon">🔗</span> Integrated
      </div>
      <div class="stat-value" id="statIntegrated">${stats.integratedRooms}</div>
    </div>

  </div>

  <!-- Quick Actions -->
  <div class="quick-actions">
    <div class="section-title">Quick Actions</div>
    <div class="action-list">
      
      <button class="action-btn" onclick="postMessage({type:'openDialog'})">
        <span class="action-btn-label">
          <span class="action-btn-icon">💬</span>
          <span>Open Fluid Dialog</span>
        </span>
        <span class="action-btn-arrow">→</span>
      </button>

      <button class="action-btn" onclick="postMessage({type:'quickAction',payload:'lock_first_room'})">
        <span class="action-btn-label">
          <span class="action-btn-icon">🔒</span>
          <span>Lock First Room</span>
        </span>
        <span class="action-btn-arrow">→</span>
      </button>

      <button class="action-btn" onclick="postMessage({type:'quickAction',payload:'verify_all'})">
        <span class="action-btn-label">
          <span class="action-btn-icon">🛡</span>
          <span>Verify All Locks</span>
        </span>
        <span class="action-btn-arrow">→</span>
      </button>

      <button class="action-btn" onclick="postMessage({type:'refreshRooms'})">
        <span class="action-btn-label">
          <span class="action-btn-icon">🔄</span>
          <span>Refresh Trees</span>
        </span>
        <span class="action-btn-arrow">→</span>
      </button>

      <button class="action-btn" onclick="postMessage({type:'viewAudit'})">
        <span class="action-btn-label">
          <span class="action-btn-icon">📜</span>
          <span>View Audit Log</span>
        </span>
        <span class="action-btn-arrow">→</span>
      </button>

    </div>
  </div>

  <!-- Footer -->
  <div class="footer">
    <strong>AiZQuad FlowStation Lab</strong><br>
    Founder: Juan Jaime Rivera Zamorano<br>
    <a href="https://github.com/aizquad/flowstation" target="_blank">
      GitHub
    </a>
  </div>

  <script>
    const vscode = acquireVsCodeApi();

    // ── Send messages TO extension ────────────────────────────
    function postMessage(msg) {
      vscode.postMessage(msg);
    }

    // ── Handle messages FROM extension ────────────────────────
    window.addEventListener('message', event => {
      const { type, payload } = event.data;

      switch (type) {

        case 'sessionUpdate':
          updateSession(payload);
          break;

        case 'statsUpdate':
          updateStats(payload);
          break;
      }
    });

    // ── Update session display ────────────────────────────────
    function updateSession(info) {
      const card  = document.getElementById('sessionCard');
      const timer = document.getElementById('sessionTimer');

      if (!card) return;

      // Update card class
      card.className = 'session-card ' + info.state;

      // Update timer if unlocked
      if (info.state === 'unlocked' && timer) {
        const minutes = Math.floor(info.timeRemaining / 60);
        const seconds = info.timeRemaining % 60;
        timer.textContent =
          String(minutes).padStart(2, '0') + ':' +
          String(seconds).padStart(2, '0');

        // Update progress ring
        updateProgressRing(info.timeRemaining);
      }
    }

    // ── Update stats cards ────────────────────────────────────
    function updateStats(stats) {
      const els = {
        statTotalRooms:   stats.totalRooms,
        statLockedRooms:  stats.lockedRooms,
        statActiveRooms:  stats.activeRooms,
        statIntegrated:   stats.integratedRooms,
      };

      for (const [id, value] of Object.entries(els)) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
      }
    }

    // ── Update progress ring (SVG) ────────────────────────────
    function updateProgressRing(seconds) {
      const circle = document.getElementById('progressCircle');
      if (!circle) return;

      const totalSeconds = 30 * 60; // 30 min default
      const percent      = seconds / totalSeconds;
      const circumference = 188.5;
      const offset       = circumference * (1 - percent);

      circle.style.strokeDashoffset = offset;
    }

    // ── Request initial update ────────────────────────────────
    postMessage({ type: 'requestUpdate' });
  </script>

</body>
</html>`;
  }

  // ── Session content renderer ────────────────────────────────

  private renderSessionContent(info: ReturnType<typeof this.session.getInfo>): string {
    if (info.state === "locked") {
      return `
        <div class="session-status">
          <div class="session-label">
            <span class="session-icon">🔒</span>
            <span>Session Locked</span>
          </div>
        </div>
        <div class="session-meta">
          Click Unlock to start working with FlowStation
        </div>
        <div class="session-actions">
          <button class="btn btn-primary" onclick="postMessage({type:'unlock'})">
            🔓 Unlock Session
          </button>
        </div>
      `;
    }

    if (info.state === "expired") {
      return `
        <div class="session-status">
          <div class="session-label">
            <span class="session-icon pulse">⏰</span>
            <span>Session Expired</span>
          </div>
        </div>
        <div class="session-meta">
          Your session timed out. Unlock to continue.
        </div>
        <div class="session-actions">
          <button class="btn btn-primary" onclick="postMessage({type:'unlock'})">
            🔓 Unlock Again
          </button>
        </div>
      `;
    }

    // Unlocked
    const minutes = Math.floor(info.timeRemaining / 60);
    const seconds = info.timeRemaining % 60;
    const timeStr = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

    return `
      <div class="session-status">
        <div class="session-label">
          <span class="session-icon">🔓</span>
          <span>Session Active</span>
        </div>
        <div class="session-timer" id="sessionTimer">${timeStr}</div>
      </div>

      <!-- Progress ring -->
      <svg class="progress-ring" viewBox="0 0 64 64">
        <circle
          id="progressCircle"
          class="progress-ring-circle"
          cx="32"
          cy="32"
          r="30"
        />
      </svg>

      <div class="session-meta">
        Unlocked at ${info.unlockedAt?.slice(11, 19) ?? "unknown"} · 
        Expires at ${info.expiresAt?.slice(11, 19) ?? "unknown"}
      </div>
      <div class="session-actions">
        <button class="btn btn-secondary" onclick="postMessage({type:'lock'})">
          🔒 Lock Now
        </button>
      </div>
    `;
  }
}
