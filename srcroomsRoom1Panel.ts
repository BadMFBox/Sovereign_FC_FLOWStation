import * as vscode from 'vscode';
import { MessageBus } from '../communication/MessageBus';
import { PipelineState } from '../pipeline/PipelineState';

export class Room1Panel {
    private panel: vscode.WebviewPanel | undefined;
    private disposables: vscode.Disposable[] = [];

    constructor(
        private readonly extensionUri: vscode.Uri,
        private readonly messageBus: MessageBus,
        private readonly pipelineState: PipelineState
    ) {}

    public show(column: vscode.ViewColumn) {
        if (this.panel) {
            this.panel.reveal(column);
            return;
        }

        this.panel = vscode.window.createWebviewPanel(
            'aizquadRoom1',
            'Command Post',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [
                    vscode.Uri.joinPath(this.extensionUri, 'src', 'webviews')
                ]
            }
        );

        this.panel.webview.html = this.getHtmlContent();

        // Handle messages from webview
        this.panel.webview.onDidReceiveMessage(
            message => this.handleMessage(message),
            null,
            this.disposables
        );

        // Update content periodically
        setInterval(() => this.updateContent(), 2000);

        this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
    }

    private async handleMessage(message: any) {
        switch (message.command) {
            case 'forge':
                vscode.commands.executeCommand('aizquad.forgeRoom');
                break;
            case 'lock':
                vscode.commands.executeCommand('aizquad.lockRoom');
                break;
            case 'split':
                const room = message.room;
                const terminal = vscode.window.activeTerminal 
                    || vscode.window.createTerminal('AiZQuad Lab');
                terminal.show();
                terminal.sendText(`make split ROOM=${room}`);
                break;
            case 'build':
                vscode.commands.executeCommand('aizquad.buildMesh');
                break;
            case 'status':
                vscode.commands.executeCommand('aizquad.labStatus');
                break;
        }
    }

    private async updateContent() {
        if (!this.panel) return;

        const state = await this.pipelineState.getState();
        
        this.panel.webview.postMessage({
            type: 'update',
            data: state
        });
    }

    private getHtmlContent(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Command Post</title>
    <style>
        body {
            padding: 20px;
            background: #1e1e1e;
            color: #d4d4d4;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        .header {
            border: 1px solid #00ffff;
            padding: 10px;
            margin-bottom: 20px;
            text-align: center;
            color: #00ffff;
            font-weight: bold;
        }
        .section {
            margin-bottom: 20px;
            border-left: 3px solid #00ffff;
            padding-left: 10px;
        }
        .section-title {
            color: #00ffff;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .room-item {
            padding: 5px;
            margin: 5px 0;
            cursor: pointer;
            border: 1px solid transparent;
        }
        .room-item:hover {
            border: 1px solid #00ffff;
            background: rgba(0, 255, 255, 0.1);
        }
        .status-locked { color: #00ff00; }
        .status-empty { color: #666; }
        .status-active { color: #ffff00; }
        .button {
            background: #00ffff;
            color: #000;
            border: none;
            padding: 8px 16px;
            margin: 5px 5px 5px 0;
            cursor: pointer;
            font-family: 'Courier New', monospace;
            font-weight: bold;
        }
        .button:hover {
            background: #00cccc;
        }
        .engine-cores {
            display: flex;
            gap: 5px;
            margin-top: 10px;
        }
        .core {
            width: 30px;
            height: 30px;
            border: 1px solid #666;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
        }
        .core-active {
            background: #00ff00;
            color: #000;
            border-color: #00ff00;
        }
        .core-idle {
            background: #1e1e1e;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="header">
        ╔═══════════════════════════════╗<br>
        ║  [ 1 ]  ◈  [ 2 ]  BMB        ║<br>
        ║  [ 4 ]  ◈  [ 3 ]  FC_FLOW    ║<br>
        ╚═══════════════════════════════╝
    </div>

    <div class="section">
        <div class="section-title">PHASE 1 — FORGE</div>
        <div id="rooms"></div>
    </div>

    <div class="section">
        <div class="section-title">PIPELINE</div>
        <button class="button" onclick="sendCommand('forge')">Forge Room</button>
        <button class="button" onclick="sendCommand('lock')">Lock Room</button>
        <button class="button" onclick="sendCommand('build')">Build Mesh</button>
    </div>

    <div class="section">
        <div class="section-title">8 CORE ENGINE</div>
        <div id="engine" class="engine-cores"></div>
    </div>

    <div class="section">
        <div class="section-title">QUICK ACTIONS</div>
        <button class="button" onclick="sendCommand('status')">Lab Status</button>
    </div>

    <script>
        const vscode = acquireVsCodeApi();

        function sendCommand(command, data = {}) {
            vscode.postMessage({ command, ...data });
        }

        window.addEventListener('message', event => {
            const message = event.data;
            if (message.type === 'update') {
                updateUI(message.data);
            }
        });

        function updateUI(state) {
            // Update rooms
            const roomsDiv = document.getElementById('rooms');
            const rooms = ['room-0', 'room-1', 'room-2', 'room-3', 'room-4', 'room-5'];
            roomsDiv.innerHTML = rooms.map(room => {
                const locked = state.lockedRooms?.includes(room);
                const status = locked ? 'locked' : 'empty';
                const icon = locked ? '🔒' : '◯';
                return \`<div class="room-item status-\${status}" onclick="sendCommand('split', {room: '\${room}'})">\${icon} \${room}</div>\`;
            }).join('');

            // Update engine cores
            const engineDiv = document.getElementById('engine');
            const activeCores = state.engineCores?.active || [];
            engineDiv.innerHTML = Array.from({length: 8}, (_, i) => i + 1).map(core => {
                const active = activeCores.includes(core);
                return \`<div class="core \${active ? 'core-active' : 'core-idle'}">\${core}</div>\`;
            }).join('');
        }

        // Initial update
        sendCommand('requestUpdate');
    </script>
</body>
</html>`;
    }

    public dispose() {
        if (this.panel) {
            this.panel.dispose();
        }

        while (this.disposables.length) {
            const disposable = this.disposables.pop();
            if (disposable) {
                disposable.dispose();
            }
        }
    }
}
