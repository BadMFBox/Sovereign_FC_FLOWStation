// ═══════════════════════════════════════════════════════════════
//  vscode-extension/src/extension.ts
//  FlowStation VS Code Integration
// ═══════════════════════════════════════════════════════════════

import * as vscode from "vscode";
import { TerminalBridge } from "./TerminalBridge";
import { AIAgent }        from "./AIAgent";

let bridge: TerminalBridge | null = null;
let agent:  AIAgent        | null = null;

export function activate(context: vscode.ExtensionContext) {

  const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (!workspaceRoot) {
    vscode.window.showErrorMessage("No workspace open");
    return;
  }

  bridge = new TerminalBridge({ workspaceRoot });
  
  const apiKey = vscode.workspace.getConfiguration("flowstation").get<string>("openaiKey");
  if (apiKey) {
    agent = new AIAgent(bridge, apiKey);
  }

  // ── Command: Unlock ─────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("flowstation.unlock", async () => {
      const pin = await vscode.window.showInputBox({
        prompt:   "Enter FlowStation PIN",
        password: true,
      });

      if (!pin) return;

      const ok = await bridge.unlock(pin);
      if (ok) {
        vscode.window.showInformationMessage("🔓 FlowStation unlocked");
        updateStatusBar("unlocked");
      } else {
        vscode.window.showErrorMessage("❌ Wrong PIN");
      }
    })
  );

  // ── Command: Lock ───────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("flowstation.lock", () => {
      bridge?.lockWorkstation();
      vscode.window.showInformationMessage("🔒 FlowStation locked");
      updateStatusBar("locked");
    })
  );

  // ── Command: Run Pipeline ───────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("flowstation.runPipeline", async () => {
      const room = await vscode.window.showInputBox({
        prompt: "Enter room name",
      });

      const version = await vscode.window.showInputBox({
        prompt: "Enter version (e.g., v1)",
      });

      if (!room || !version) return;

      vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title:    `Running FlowStation pipeline: ${room}`,
        },
        async () => {
          await bridge?.runFullPipeline(room, version);
          vscode.window.showInformationMessage(
            `✅ Pipeline complete: ${room}`
          );
        }
      );
    })
  );

  // ── Command: AI Chat ────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("flowstation.aiChat", async () => {
      if (!agent) {
        vscode.window.showErrorMessage(
          "OpenAI key not configured. Set flowstation.openaiKey in settings."
        );
        return;
      }

      const room = await vscode.window.showQuickPick(
        bridge?.listMeshRooms() ?? [],
        { placeHolder: "Select a room" }
      );

      if (!room) return;

      const query = await vscode.window.showInputBox({
        prompt: `Ask about ${room}`,
      });

      if (!query) return;

      const response = await agent.ask({ room, query, context: "surface" });
      
      const panel = vscode.window.createWebviewPanel(
        "flowstationAI",
        `FlowStation AI: ${room}`,
        vscode.ViewColumn.Two,
        {}
      );

      panel.webview.html = `
        <html>
        <body>
          <h2>Query: ${query}</h2>
          <p><strong>Access Level:</strong> ${response.accessUsed}</p>
          <pre>${response.answer}</pre>
          <p><em>Tokens: ${response.tokensUsed}</em></p>
        </body>
        </html>
      `;
    })
  );

  // ── Status Bar ──────────────────────────────────────────────
  const statusBar = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    100
  );
  statusBar.text    = "🔒 FlowStation";
  statusBar.command = "flowstation.unlock";
  statusBar.show();
  context.subscriptions.push(statusBar);

  function updateStatusBar(state: "locked" | "unlocked") {
    if (state === "unlocked") {
      const remaining = bridge?.sessionTimeRemaining() ?? 0;
      const minutes   = Math.floor(remaining / 60);
      statusBar.text  = `🔓 FlowStation (${minutes}m)`;
      statusBar.command = "flowstation.lock";
    } else {
      statusBar.text    = "🔒 FlowStation";
      statusBar.command = "flowstation.unlock";
    }
  }
}

export function deactivate() {
  bridge?.destroy();
}
