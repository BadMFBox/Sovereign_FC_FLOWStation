import * as vscode from 'vscode';
import { Room1Panel } from './rooms/Room1Panel';
import { Room2Panel } from './rooms/Room2Panel';
import { LayoutManager } from './rooms/LayoutManager';
import { PipelineState } from './pipeline/PipelineState';
import { MessageBus } from './communication/MessageBus';

let room1Panel: Room1Panel | undefined;
let room2Panel: Room2Panel | undefined;
let layoutManager: LayoutManager;
let messageBus: MessageBus;
let pipelineState: PipelineState;

export function activate(context: vscode.ExtensionContext) {
    console.log('AiZQuad IDE is now active');

    // Initialize core systems
    messageBus = new MessageBus();
    pipelineState = new PipelineState(context);
    layoutManager = new LayoutManager(context);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('aizquad.openIDE', () => {
            openAiZQuadIDE(context);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('aizquad.forgeRoom', async () => {
            const room = await vscode.window.showQuickPick(
                ['room-0', 'room-1', 'room-2', 'room-3', 'room-4', 'room-5'],
                { placeHolder: 'Select room to forge' }
            );
            if (room) {
                executeInTerminal(`make forge ROOM=${room}`);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('aizquad.lockRoom', async () => {
            const room = await vscode.window.showQuickPick(
                ['room-0', 'room-1', 'room-2', 'room-3', 'room-4', 'room-5'],
                { placeHolder: 'Select room to lock' }
            );
            if (room) {
                const version = await vscode.window.showInputBox({
                    prompt: 'Version (e.g., v1)',
                    value: 'v1'
                });
                if (version) {
                    executeInTerminal(`make lock ROOM=${room} V=${version}`);
                }
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('aizquad.buildMesh', () => {
            executeInTerminal('make build');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('aizquad.labStatus', () => {
            executeInTerminal('make lab-status');
        })
    );

    // Auto-open IDE if configured
    const config = vscode.workspace.getConfiguration('aizquad');
    if (config.get('autoOpenIDE')) {
        openAiZQuadIDE(context);
    }

    // Show welcome message
    vscode.window.showInformationMessage(
        '🔥 AiZQuad IDE activated — The Bad MF Box is ready',
        'Open IDE'
    ).then(selection => {
        if (selection === 'Open IDE') {
            vscode.commands.executeCommand('aizquad.openIDE');
        }
    });
}

function openAiZQuadIDE(context: vscode.ExtensionContext) {
    // Create Room 1 (Command Post - top left)
    if (!room1Panel) {
        room1Panel = new Room1Panel(context.extensionUri, messageBus, pipelineState);
    }
    room1Panel.show(vscode.ViewColumn.One);

    // Create Room 2 (File Status - top right)
    if (!room2Panel) {
        room2Panel = new Room2Panel(context.extensionUri, messageBus, pipelineState);
    }
    room2Panel.show(vscode.ViewColumn.Two);

    // Room 3 (Terminal) and Room 4 (Copilot Chat) are handled by layout manager
    layoutManager.setupLayout();

    vscode.window.showInformationMessage(
        '╔═══════════════════════════════════╗\n' +
        '║  [ 1 ]  ◈  [ 2 ]  BMB            ║\n' +
        '║  [ 4 ]  ◈  [ 3 ]  FC_FLOW MESH   ║\n' +
        '╚═══════════════════════════════════╝'
    );
}

function executeInTerminal(command: string) {
    const terminal = vscode.window.terminals.find(t => t.name === 'AiZQuad Lab') 
        || vscode.window.createTerminal('AiZQuad Lab');
    
    terminal.show();
    terminal.sendText(command);
}

export function deactivate() {
    console.log('AiZQuad IDE deactivated');
}
// ═══════════════════════════════════════════════════════════════
//  extension.ts — FlowStation VS Code Extension Entry Point
//  AiZQuad FlowStation Lab
//  Founder: Juan Jaime Rivera Zamorano
// ═══════════════════════════════════════════════════════════════

import * as vscode from "vscode";
import { SessionManager }   from "./SessionManager";
import { StatusBarManager } from "./StatusBarManager";
import { RoomTreeView }     from "./RoomTreeView";
import { MeshTreeView }     from "./MeshTreeView";
import { AuditTreeView }    from "./AuditTreeView";
import { DialogPanel }      from "./DialogPanel";
import { SessionPanel }     from "./SessionPanel";
import { CommandRegistry }  from "./CommandRegistry";
import { BridgeConnector }  from "./BridgeConnector";

// Global instances — shared across all components
export let bridge:     BridgeConnector;
export let session:    SessionManager;
export let statusBar:  StatusBarManager;

export async function activate(
  context: vscode.ExtensionContext
): Promise<void> {

  // ── Resolve workspace root ─────────────────────────────────
  const workspaceRoot =
    vscode.workspace.getConfiguration("flowstation").get<string>("workspaceRoot") ||
    vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

  if (!workspaceRoot) {
    vscode.window.showErrorMessage(
      "FlowStation: No workspace found. Open a folder first."
    );
    return;
  }

  // ── Core services ──────────────────────────────────────────
  bridge    = new BridgeConnector(workspaceRoot);
  session   = new SessionManager(context, bridge);
  statusBar = new StatusBarManager(context, session);

  // ── Tree views ─────────────────────────────────────────────
  const roomTree  = new RoomTreeView(bridge, session);
  const meshTree  = new MeshTreeView(bridge, session);
  const auditTree = new AuditTreeView(bridge, session);

  vscode.window.registerTreeDataProvider(
    "flowstation.rooms", roomTree
  );
  vscode.window.registerTreeDataProvider(
    "flowstation.mesh", meshTree
  );
  vscode.window.registerTreeDataProvider(
    "flowstation.audit", auditTree
  );

  // ── Session panel (webview in sidebar) ────────────────────
  const sessionPanel = new SessionPanel(
    context, bridge, session
  );
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      "flowstation.session",
      sessionPanel
    )
  );

  // ── Commands ───────────────────────────────────────────────
  const registry = new CommandRegistry(
    context,
    bridge,
    session,
    roomTree,
    meshTree,
    auditTree
  );
  registry.registerAll();

  // ── Auto-refresh on file save ──────────────────────────────
  const config = vscode.workspace.getConfiguration("flowstation");
  if (config.get<boolean>("autoScan")) {
    context.subscriptions.push(
      vscode.workspace.onDidSaveTextDocument(doc => {
        if (doc.uri.fsPath.includes("forge/active")) {
          roomTree.refresh();
        }
      })
    );
  }

  // ── Session tick — update status bar every 30s ─────────────
  const tick = setInterval(() => {
    statusBar.update();
    if (session.isExpired()) {
      session.expire();
      vscode.window.showWarningMessage(
        "FlowStation: Session expired. Unlock to continue."
      );
    }
  }, 30_000);

  context.subscriptions.push({
    dispose: () => clearInterval(tick)
  });

  // ── Welcome message (first time) ──────────────────────────
  const hasSeenWelcome = context.globalState.get("flowstation.welcomed");
  if (!hasSeenWelcome) {
    vscode.window.showInformationMessage(
      "⚡ FlowStation is ready. Unlock to start.",
      "Unlock Now"
    ).then(choice => {
      if (choice === "Unlock Now") {
        vscode.commands.executeCommand("flowstation.unlock");
      }
    });
    context.globalState.update("flowstation.welcomed", true);
  }

  console.log("⚡ FlowStation Lab activated");
}

export function deactivate(): void {
  bridge?.destroy();
  session?.destroy();
  statusBar?.destroy();
}
// ═══════════════════════════════════════════════════════════════
//  extension.ts — FlowStation VS Code Extension Entry Point
//  AiZQuad FlowStation Lab
//  Founder: Juan Jaime Rivera Zamorano
// ═══════════════════════════════════════════════════════════════

import * as vscode from "vscode";
import { SessionManager }   from "./SessionManager";
import { StatusBarManager } from "./StatusBarManager";
import { RoomTreeView }     from "./RoomTreeView";
import { MeshTreeView }     from "./MeshTreeView";
import { AuditTreeView }    from "./AuditTreeView";
import { DialogPanel }      from "./DialogPanel";
import { SessionPanel }     from "./SessionPanel";
import { CommandRegistry }  from "./CommandRegistry";
import { BridgeConnector }  from "./BridgeConnector";

// Global instances — shared across all components
export let bridge:     BridgeConnector;
export let session:    SessionManager;
export let statusBar:  StatusBarManager;

export async function activate(
  context: vscode.ExtensionContext
): Promise<void> {

  // ── Resolve workspace root ─────────────────────────────────
  const workspaceRoot =
    vscode.workspace.getConfiguration("flowstation").get<string>("workspaceRoot") ||
    vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

  if (!workspaceRoot) {
    vscode.window.showErrorMessage(
      "FlowStation: No workspace found. Open a folder first."
    );
    return;
  }

  // ── Core services ──────────────────────────────────────────
  bridge    = new BridgeConnector(workspaceRoot);
  session   = new SessionManager(context, bridge);
  statusBar = new StatusBarManager(context, session);

  // ── Tree views ─────────────────────────────────────────────
  const roomTree  = new RoomTreeView(bridge, session);
  const meshTree  = new MeshTreeView(bridge, session);
  const auditTree = new AuditTreeView(bridge, session);

  vscode.window.registerTreeDataProvider(
    "flowstation.rooms", roomTree
  );
  vscode.window.registerTreeDataProvider(
    "flowstation.mesh", meshTree
  );
  vscode.window.registerTreeDataProvider(
    "flowstation.audit", auditTree
  );

  // ── Session panel (webview in sidebar) ────────────────────
  const sessionPanel = new SessionPanel(
    context, bridge, session
  );
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      "flowstation.session",
      sessionPanel
    )
  );

  // ── Commands ───────────────────────────────────────────────
  const registry = new CommandRegistry(
    context,
    bridge,
    session,
    roomTree,
    meshTree,
    auditTree
  );
  registry.registerAll();

  // ── Auto-refresh on file save ──────────────────────────────
  const config = vscode.workspace.getConfiguration("flowstation");
  if (config.get<boolean>("autoScan")) {
    context.subscriptions.push(
      vscode.workspace.onDidSaveTextDocument(doc => {
        if (doc.uri.fsPath.includes("forge/active")) {
          roomTree.refresh();
        }
      })
    );
  }

  // ── Session tick — update status bar every 30s ─────────────
  const tick = setInterval(() => {
    statusBar.update();
    if (session.isExpired()) {
      session.expire();
      vscode.window.showWarningMessage(
        "FlowStation: Session expired. Unlock to continue."
      );
    }
  }, 30_000);

  context.subscriptions.push({
    dispose: () => clearInterval(tick)
  });

  // ── Welcome message (first time) ──────────────────────────
  const hasSeenWelcome = context.globalState.get("flowstation.welcomed");
  if (!hasSeenWelcome) {
    vscode.window.showInformationMessage(
      "⚡ FlowStation is ready. Unlock to start.",
      "Unlock Now"
    ).then(choice => {
      if (choice === "Unlock Now") {
        vscode.commands.executeCommand("flowstation.unlock");
      }
    });
    context.globalState.update("flowstation.welcomed", true);
  }

  console.log("⚡ FlowStation Lab activated");
}

export function deactivate(): void {
  bridge?.destroy();
  session?.destroy();
  statusBar?.destroy();
}
// Update deactivate() in extension.ts
// to clean up the new tree views

export function deactivate(): void {
  bridge?.destroy();
  session?.destroy();
  statusBar?.destroy();

  // Trees implement dispose() — call them too
  // (VS Code calls dispose on context.subscriptions automatically
  //  if you push them there — but explicit is better)
}

// And in activate(), push the tree disposables:
context.subscriptions.push(
  { dispose: () => (roomTree  as any).dispose?.() },
  { dispose: () => (meshTree  as any).dispose?.() },
  { dispose: () => (auditTree as any).dispose?.() },
);
// In extension.ts activate(), you already have:

const sessionPanel = new SessionPanel(
  context, bridge, session
);
context.subscriptions.push(
  vscode.window.registerWebviewViewProvider(
    "flowstation.session",
    sessionPanel
  )
);

// ✅ Already done — SessionPanel is now live
