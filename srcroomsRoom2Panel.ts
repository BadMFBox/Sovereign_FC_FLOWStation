import * as vscode from 'vscode';
import * as path from 'path';
import { MessageBus } from '../communication/MessageBus';
import { PipelineState } from '../pipeline/PipelineState';

export class Room2Panel {
    private panel: vscode.WebviewPanel | undefined;
    private disposables: vscode.Disposable[] = [];
    private currentFile: string = '';

    constructor(
        private readonly extensionUri: vscode.Uri,
        private readonly messageBus: MessageBus,
        private readonly pipelineState: PipelineState
    ) {
        // Watch for active editor changes
        vscode.window.onDidChangeActiveTextEditor(editor => {
            if (editor) {
                this.currentFile = editor.document.fileName;
                this.updateContent();
            }
        });

        // Watch for file saves
        vscode.workspace.onDidSaveTextDocument(doc => {
            this.updateContent();
        });
    }

    public show(column: vscode.ViewColumn) {
        if (this.panel) {
            this.panel.reveal(column);
            return;
        }

        this.panel = vscode.window.createWebviewPanel(
            'aizquadRoom2',
            'File Status',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true
            }
        );

        this.panel.webview.html = this.getHtmlContent();

        // Update immediately and periodically
        this.updateContent();
        setInterval(() => this.updateContent(), 3000);

        this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
    }

    private async updateContent() {
        if (!this.panel) return;

        const editor = vscode.window.activeTextEditor;
        const fileInfo = editor ? {
            fileName: path.basename(editor.document.fileName),
            fullPath: editor.document.fileName,
            isDirty: editor.document.isDirty,
            lineCount: editor.document.lineCount,
            language: editor.document.languageId
        } : null;

        const state = await this.pipelineState.getState();

        this.panel.webview.postMessage({
            type: 'update',
            file: fileInfo,
            pipeline: state
        });
    }

    private getHtmlContent(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Status</title>
    <style>
        body {
            padding: 20px;
            background: #1e1e1e;
            color: #d4d4d4;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        .header {
            color: #00ffff;
            font-weight: bold;
            border-bottom: 1px solid #00ffff;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .section {
            margin-bottom: 20px;
        }
        .label {
            color: #888;
            display: inline-block;
            width: 120px;
        }
        .value {
            color: #d4d4d4;
        }
        .status-good { color: #00ff00; }
        .status-warn { color: #ffff00; }
        .status-error { color: #ff0000; }
        .pipeline-track {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            align-items: center;
        }
        .phase {
            padding: 5px 10px;
            border: 1px solid #666;
            font-size: 11px;
        }
        .phase-active {
            background: #00ffff;
            color: #000;
            border-color: #00ffff;
        }
        .phase-complete {
            background: #00ff00;
            color: #000;
            border-color: #00ff00;
        }
        .arrow {
            color: #666;
        }
    </style>
</head>
<body>
    <div class="header">FILE STATUS — ROOM 2</div>

    <div class="section">
        <div><span class="label">Current File:</span><span id="fileName" class="value">—</span></div>
        <div><span class="label">Path:</span><span id="filePath" class="value status-dim">—</span></div>
        <div><span class="label">Status:</span><span id="fileStatus" class="value">—</span></div>
        <div><span class="label">Lines:</span><span id="lineCount" class="value">—</span></div>
        <div><span class="label">Language:</span><span id="language" class="value">—</span></div>
    </div>

    <div class="section">
        <div class="header">PIPELINE POSITION</div>
        <div class="pipeline-track" id="pipeline"></div>
    </div>

    <div class="section">
        <div class="header">RECENT ACTIVITY</div>
        <div id="activity" style="font-size: 12px; color: #888;">
            • Waiting for activity...
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();

        window.addEventListener('message', event => {
            const message = event.data;
            if (message.type === 'update') {
                updateFileInfo(message.file);
                updatePipeline(message.pipeline);
            }
        });

        function updateFileInfo(file) {
            if (!file) {
                document.getElementById('fileName').textContent = 'No file open';
                return;
            }

            document.getElementById('fileName').textContent = file.fileName;
            document.getElementById('filePath').textContent = file.fullPath;
            document.getElementById('fileStatus').textContent = file.isDirty ? '🔴 Modified' : '✅ Saved';
            document.getElementById('lineCount').textContent = file.lineCount;
            document.getElementById('language').textContent = file.language;
        }

        function updatePipeline(state) {
            const phases = ['FORGE', 'SPLIT', 'SORT', 'INTEGRATE'];
            const pipelineDiv = document.getElementById('pipeline');
            
            pipelineDiv.innerHTML = phases.map((phase, i) => {
                const className = 'phase'; // Update based on actual state
                return \`<div class="\${className}">\${phase}</div>\` + 
                       (i < phases.length - 1 ? '<span class="arrow">→</span>' : '');
            }).join('');
        }
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
